"""
Cog de auto-moderação.
Implementa detecção automática de spam, raids, nukes e conteúdo inadequado.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Optional, Dict, Deque
import re
import structlog

from utils.embeds import automod_embed, raid_alert_embed, nuke_alert_embed, error_embed
from utils.permissions import get_mute_role
from utils.errors import safe_send, safe_delete

logger = structlog.get_logger()


class AutoModCog(commands.Cog, name="Auto-Moderação"):
    """Sistema automático de moderação."""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Cache de mensagens por usuário (para detecção de spam)
        self.user_messages: Dict[int, Dict[int, Deque]] = defaultdict(lambda: defaultdict(deque))
        
        # Cache de joins recentes (para detecção de raid)
        self.recent_joins: Dict[int, Deque] = defaultdict(deque)
        
        # Cache de ações de canal/cargo (para detecção de nuke)
        self.channel_actions: Dict[int, Deque] = defaultdict(deque)
        self.role_actions: Dict[int, Deque] = defaultdict(deque)
        
        # Regex patterns
        self.url_pattern = re.compile(r'https?://[^\s]+')
        self.invite_pattern = re.compile(r'discord(?:\.gg|\.com/invite)/[a-zA-Z0-9]+')
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitora mensagens para auto-moderação."""
        # Ignorar bots e DMs
        if message.author.bot or not message.guild:
            return
        
        # Ignorar moderadores
        if message.author.guild_permissions.manage_messages:
            return
        
        try:
            config = await self.bot.get_guild_config(message.guild.id)
            automod_config = config.get('automod', {})
            
            if not automod_config.get('enabled', True):
                return
            
            # Verificar spam
            if automod_config.get('spam', {}).get('enabled', True):
                if await self._check_spam(message, automod_config['spam']):
                    return  # Mensagem já foi tratada
            
            # Verificar links
            if automod_config.get('links', {}).get('enabled', True):
                if await self._check_links(message, automod_config['links']):
                    return
            
            # Verificar convites
            if automod_config.get('invites', {}).get('enabled', True):
                if await self._check_invites(message, automod_config['invites']):
                    return
            
            # Verificar palavras proibidas
            if automod_config.get('bad_words', {}).get('enabled', True):
                if await self._check_bad_words(message, automod_config['bad_words']):
                    return
            
            # Verificar anexos
            if automod_config.get('attachments', {}).get('enabled', False):
                if await self._check_attachments(message, automod_config['attachments']):
                    return
                    
        except Exception as e:
            await logger.aerror("Erro no automod on_message", error=str(e))
    
    async def _check_spam(self, message: discord.Message, spam_config: dict) -> bool:
        """
        Verifica se a mensagem é spam.
        
        Returns:
            True se spam foi detectado e ação foi tomada
        """
        max_messages = spam_config.get('max_messages', 5)
        time_window = spam_config.get('time_window', 5)
        action = spam_config.get('action', 'mute')
        duration = spam_config.get('duration', 300)
        
        # Adicionar mensagem ao cache
        user_id = message.author.id
        guild_id = message.guild.id
        
        now = datetime.utcnow()
        self.user_messages[guild_id][user_id].append((now, message.content))
        
        # Limpar mensagens antigas
        cutoff = now - timedelta(seconds=time_window)
        while self.user_messages[guild_id][user_id] and self.user_messages[guild_id][user_id][0][0] < cutoff:
            self.user_messages[guild_id][user_id].popleft()
        
        # Verificar se excedeu o limite
        if len(self.user_messages[guild_id][user_id]) >= max_messages:
            # Verificar se as mensagens são similares
            messages = [msg[1] for msg in self.user_messages[guild_id][user_id]]
            if len(set(messages)) <= 2:  # Mensagens muito similares
                await self._take_action(
                    message.author,
                    message.guild,
                    'spam',
                    action,
                    duration,
                    f"Spam detectado: {len(messages)} mensagens em {time_window}s"
                )
                
                # Deletar mensagens de spam
                try:
                    await message.channel.purge(
                        limit=max_messages,
                        check=lambda m: m.author.id == user_id
                    )
                except:
                    pass
                
                # Limpar cache
                self.user_messages[guild_id][user_id].clear()
                
                return True
        
        return False
    
    async def _check_links(self, message: discord.Message, links_config: dict) -> bool:
        """Verifica links na mensagem."""
        urls = self.url_pattern.findall(message.content)
        
        if not urls:
            return False
        
        whitelist = links_config.get('whitelist', [])
        blacklist = links_config.get('blacklist', [])
        action = links_config.get('action', 'warn')
        
        # Verificar blacklist
        for url in urls:
            for blocked in blacklist:
                if blocked.lower() in url.lower():
                    await safe_delete(message)
                    await self._take_action(
                        message.author,
                        message.guild,
                        'blocked_link',
                        action,
                        300,
                        f"Link bloqueado: {url}"
                    )
                    return True
        
        # Se houver whitelist, verificar se o link está nela
        if whitelist:
            for url in urls:
                allowed = False
                for allowed_domain in whitelist:
                    if allowed_domain.lower() in url.lower():
                        allowed = True
                        break
                
                if not allowed:
                    await safe_delete(message)
                    await self._take_action(
                        message.author,
                        message.guild,
                        'unauthorized_link',
                        action,
                        300,
                        f"Link não autorizado: {url}"
                    )
                    return True
        
        return False
    
    async def _check_invites(self, message: discord.Message, invites_config: dict) -> bool:
        """Verifica convites do Discord."""
        invites = self.invite_pattern.findall(message.content)
        
        if not invites:
            return False
        
        whitelist = invites_config.get('whitelist', [])
        action = invites_config.get('action', 'delete')
        
        # Se houver whitelist, verificar
        if whitelist:
            for invite in invites:
                if invite not in whitelist:
                    await safe_delete(message)
                    await self._take_action(
                        message.author,
                        message.guild,
                        'unauthorized_invite',
                        action,
                        300,
                        f"Convite não autorizado detectado"
                    )
                    return True
        else:
            # Sem whitelist, bloquear todos os convites
            await safe_delete(message)
            await self._take_action(
                message.author,
                message.guild,
                'invite',
                action,
                300,
                "Convite do Discord detectado"
            )
            return True
        
        return False
    
    async def _check_bad_words(self, message: discord.Message, bad_words_config: dict) -> bool:
        """Verifica palavras proibidas."""
        bad_words = bad_words_config.get('words', [])
        action = bad_words_config.get('action', 'warn')
        
        if not bad_words:
            return False
        
        content_lower = message.content.lower()
        
        for word in bad_words:
            if word.lower() in content_lower:
                await safe_delete(message)
                await self._take_action(
                    message.author,
                    message.guild,
                    'bad_word',
                    action,
                    300,
                    f"Linguagem inadequada detectada"
                )
                return True
        
        return False
    
    async def _check_attachments(self, message: discord.Message, attachments_config: dict) -> bool:
        """Verifica anexos suspeitos."""
        if not message.attachments:
            return False
        
        max_size_mb = attachments_config.get('max_size_mb', 8)
        blocked_extensions = attachments_config.get('blocked_extensions', [])
        action = attachments_config.get('action', 'delete')
        
        for attachment in message.attachments:
            # Verificar tamanho
            size_mb = attachment.size / (1024 * 1024)
            if size_mb > max_size_mb:
                await safe_delete(message)
                await self._take_action(
                    message.author,
                    message.guild,
                    'large_attachment',
                    action,
                    300,
                    f"Anexo muito grande: {size_mb:.1f}MB"
                )
                return True
            
            # Verificar extensão
            for ext in blocked_extensions:
                if attachment.filename.lower().endswith(ext.lower()):
                    await safe_delete(message)
                    await self._take_action(
                        message.author,
                        message.guild,
                        'blocked_attachment',
                        action,
                        300,
                        f"Tipo de arquivo bloqueado: {ext}"
                    )
                    return True
        
        return False
    
    async def _take_action(
        self,
        member: discord.Member,
        guild: discord.Guild,
        event_type: str,
        action: str,
        duration: int,
        reason: str
    ):
        """Executa ação de auto-moderação."""
        try:
            # Registrar evento
            await self.bot.db.log_automod_event(
                guild.id,
                member.id,
                event_type,
                reason,
                action
            )
            
            # Executar ação
            if action == 'delete':
                # Apenas deletar (já foi feito)
                pass
            
            elif action == 'warn':
                # Adicionar advertência
                await self.bot.db.add_infraction(
                    member.id,
                    guild.id,
                    self.bot.user.id,
                    'warn',
                    f"[AUTOMOD] {reason}"
                )
                
                # Notificar usuário
                try:
                    embed = error_embed(
                        "⚠️ Advertência Automática",
                        f"Você recebeu uma advertência em **{guild.name}**.\n\n**Motivo:** {reason}"
                    )
                    await safe_send(member, embed=embed)
                except:
                    pass
            
            elif action == 'mute':
                # Silenciar usuário
                mute_role = await get_mute_role(guild)
                await member.add_roles(mute_role, reason=f"[AUTOMOD] {reason}")
                
                expires_at = datetime.utcnow() + timedelta(seconds=duration)
                
                await self.bot.db.add_mute(
                    member.id,
                    guild.id,
                    self.bot.user.id,
                    f"[AUTOMOD] {reason}",
                    expires_at
                )
                
                # Notificar usuário
                try:
                    embed = error_embed(
                        "🔇 Você foi silenciado automaticamente",
                        f"**Servidor:** {guild.name}\n"
                        f"**Motivo:** {reason}\n"
                        f"**Duração:** {duration // 60} minutos"
                    )
                    await safe_send(member, embed=embed)
                except:
                    pass
            
            elif action == 'kick':
                # Expulsar
                await self.bot.db.add_infraction(
                    member.id,
                    guild.id,
                    self.bot.user.id,
                    'kick',
                    f"[AUTOMOD] {reason}"
                )
                
                await guild.kick(member, reason=f"[AUTOMOD] {reason}")
            
            elif action == 'ban':
                # Banir
                await self.bot.db.add_infraction(
                    member.id,
                    guild.id,
                    self.bot.user.id,
                    'ban',
                    f"[AUTOMOD] {reason}"
                )
                
                await guild.ban(member, reason=f"[AUTOMOD] {reason}")
            
            await logger.ainfo(
                "Ação de automod executada",
                user=str(member),
                guild=guild.name,
                event_type=event_type,
                action=action,
                reason=reason
            )
            
        except Exception as e:
            await logger.aerror("Erro ao executar ação de automod", error=str(e))
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Monitora entradas para detectar raids."""
        try:
            config = await self.bot.get_guild_config(member.guild.id)
            antiraid_config = config.get('anti_raid', {})
            
            if not antiraid_config.get('enabled', True):
                return
            
            # Adicionar ao cache
            now = datetime.utcnow()
            self.recent_joins[member.guild.id].append(now)
            
            # Limpar joins antigos
            time_window = antiraid_config.get('time_window', 60)
            cutoff = now - timedelta(seconds=time_window)
            
            while self.recent_joins[member.guild.id] and self.recent_joins[member.guild.id][0] < cutoff:
                self.recent_joins[member.guild.id].popleft()
            
            # Verificar threshold
            join_count = len(self.recent_joins[member.guild.id])
            threshold = antiraid_config.get('join_threshold', 10)
            
            if join_count >= threshold:
                await self._handle_raid(member.guild, join_count, time_window, antiraid_config)
                
        except Exception as e:
            await logger.aerror("Erro no anti-raid", error=str(e))
    
    async def _handle_raid(
        self,
        guild: discord.Guild,
        join_count: int,
        time_window: int,
        config: dict
    ):
        """Trata detecção de raid."""
        await logger.awarning(
            "RAID DETECTADO",
            guild=guild.name,
            join_count=join_count,
            time_window=time_window
        )
        
        action_taken = "Alerta enviado aos moderadores"
        
        # Auto-lockdown se configurado
        if config.get('auto_lockdown', True):
            # Desabilitar convites
            try:
                invites = await guild.invites()
                for invite in invites:
                    try:
                        await invite.delete(reason="Auto-lockdown: Raid detectado")
                    except:
                        pass
                
                action_taken = "Lockdown ativado: convites desabilitados"
                
            except Exception as e:
                await logger.aerror("Erro ao ativar lockdown", error=str(e))
        
        # Enviar alerta
        log_config = (await self.bot.get_guild_config(guild.id)).get('logging', {})
        log_channel_id = log_config.get('log_channel_id')
        
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                embed = raid_alert_embed(join_count, time_window, action_taken)
                await safe_send(log_channel, embed=embed)
        
        # Limpar cache
        self.recent_joins[guild.id].clear()
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Monitora deleção de canais para detectar nuke."""
        await self._check_nuke_action(channel.guild, 'channel_delete')
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Monitora criação de canais para detectar nuke."""
        await self._check_nuke_action(channel.guild, 'channel_create')
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Monitora deleção de cargos para detectar nuke."""
        await self._check_nuke_action(role.guild, 'role_delete')
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Monitora criação de cargos para detectar nuke."""
        await self._check_nuke_action(role.guild, 'role_create')
    
    async def _check_nuke_action(self, guild: discord.Guild, action_type: str):
        """Verifica se há atividade de nuke."""
        try:
            config = await self.bot.get_guild_config(guild.id)
            antinuke_config = config.get('anti_nuke', {})
            
            if not antinuke_config.get('enabled', True):
                return
            
            # Adicionar ao cache apropriado
            now = datetime.utcnow()
            
            if 'channel' in action_type:
                self.channel_actions[guild.id].append(now)
                actions_cache = self.channel_actions[guild.id]
                threshold = antinuke_config.get('channel_threshold', 5)
            else:
                self.role_actions[guild.id].append(now)
                actions_cache = self.role_actions[guild.id]
                threshold = antinuke_config.get('role_threshold', 5)
            
            # Limpar ações antigas
            time_window = antinuke_config.get('time_window', 60)
            cutoff = now - timedelta(seconds=time_window)
            
            while actions_cache and actions_cache[0] < cutoff:
                actions_cache.popleft()
            
            # Verificar threshold
            if len(actions_cache) >= threshold:
                await self._handle_nuke(guild, action_type, len(actions_cache))
                actions_cache.clear()
                
        except Exception as e:
            await logger.aerror("Erro no anti-nuke", error=str(e))
    
    async def _handle_nuke(self, guild: discord.Guild, action_type: str, count: int):
        """Trata detecção de nuke."""
        await logger.awarning(
            "NUKE DETECTADO",
            guild=guild.name,
            action_type=action_type,
            count=count
        )
        
        # Tentar identificar o responsável via audit log
        actor = None
        try:
            async for entry in guild.audit_logs(limit=10):
                if 'channel' in action_type and entry.action in [
                    discord.AuditLogAction.channel_create,
                    discord.AuditLogAction.channel_delete
                ]:
                    actor = entry.user
                    break
                elif 'role' in action_type and entry.action in [
                    discord.AuditLogAction.role_create,
                    discord.AuditLogAction.role_delete
                ]:
                    actor = entry.user
                    break
        except:
            pass
        
        # Enviar alerta
        log_config = (await self.bot.get_guild_config(guild.id)).get('logging', {})
        log_channel_id = log_config.get('log_channel_id')
        
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                embed = nuke_alert_embed(action_type, count, actor)
                await safe_send(log_channel, embed=embed)


async def setup(bot):
    """Registra o cog no bot."""
    await bot.add_cog(AutoModCog(bot))
