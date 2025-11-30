"""
Sistema de agendamento de tarefas periódicas.
Gerencia expiração de mutes, tempbans e outras tarefas recorrentes.
"""

import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from typing import Optional
import structlog

from .database import Database
from .errors import safe_send
from .embeds import info_embed

logger = structlog.get_logger()


class TaskScheduler:
    """Gerenciador de tarefas agendadas."""
    
    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.db = database
        self.check_expirations.start()
        self.cleanup_old_data.start()
    
    def cog_unload(self):
        """Para as tarefas ao descarregar."""
        self.check_expirations.cancel()
        self.cleanup_old_data.cancel()
    
    @tasks.loop(minutes=1)
    async def check_expirations(self):
        """Verifica e processa mutes e bans expirados."""
        try:
            # Processar mutes expirados
            await self._process_expired_mutes()
            
            # Processar bans temporários expirados
            await self._process_expired_bans()
            
        except Exception as e:
            await logger.aerror("Erro ao verificar expirações", error=str(e))
    
    @check_expirations.before_loop
    async def before_check_expirations(self):
        """Aguarda o bot estar pronto antes de iniciar."""
        await self.bot.wait_until_ready()
        await logger.ainfo("Scheduler de expirações iniciado")
    
    async def _process_expired_mutes(self):
        """Processa mutes expirados."""
        expired_mutes = await self.db.get_expired_mutes()
        
        for mute in expired_mutes:
            try:
                guild_id = mute.get('guild_id')
                user_id = mute.get('user_id')
                
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await logger.awarning("Guild não encontrada para unmute", guild_id=guild_id)
                    await self.db.remove_mute(user_id, guild_id)
                    continue
                
                member = guild.get_member(user_id)
                if not member:
                    await logger.adebug("Membro não encontrado para unmute", user_id=user_id)
                    await self.db.remove_mute(user_id, guild_id)
                    continue
                
                # Remover cargo de mute
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if mute_role and mute_role in member.roles:
                    await member.remove_roles(mute_role, reason="Mute expirado automaticamente")
                    await logger.ainfo("Mute expirado removido", user=str(member), guild=guild.name)
                
                # Atualizar banco de dados
                await self.db.remove_mute(user_id, guild_id)
                
                # Notificar o usuário
                try:
                    embed = info_embed(
                        "Mute Expirado",
                        f"Seu mute em **{guild.name}** expirou. Você pode voltar a enviar mensagens."
                    )
                    await safe_send(member, embed=embed)
                except:
                    pass  # Ignorar se não conseguir enviar DM
                
            except Exception as e:
                await logger.aerror("Erro ao processar mute expirado", mute_id=mute.get('id'), error=str(e))
    
    async def _process_expired_bans(self):
        """Processa bans temporários expirados."""
        expired_bans = await self.db.get_expired_bans()
        
        for ban in expired_bans:
            try:
                guild_id = ban.get('guild_id')
                user_id = ban.get('user_id')
                
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await logger.awarning("Guild não encontrada para unban", guild_id=guild_id)
                    continue
                
                # Tentar desbanir
                try:
                    user = await self.bot.fetch_user(user_id)
                    await guild.unban(user, reason="Ban temporário expirado automaticamente")
                    await logger.ainfo("Ban temporário expirado removido", user_id=user_id, guild=guild.name)
                    
                    # Atualizar banco de dados
                    if self.db.db_type == "sqlite":
                        await self.db.conn.execute(
                            "UPDATE infractions SET active = 0 WHERE id = ?",
                            (ban.get('id'),)
                        )
                        await self.db.conn.commit()
                    else:
                        await self.db.conn.execute(
                            "UPDATE infractions SET active = 0 WHERE id = $1",
                            ban.get('id')
                        )
                    
                    # Notificar o usuário
                    try:
                        embed = info_embed(
                            "Ban Temporário Expirado",
                            f"Seu ban temporário em **{guild.name}** expirou. Você pode voltar ao servidor."
                        )
                        await safe_send(user, embed=embed)
                    except:
                        pass
                    
                except discord.NotFound:
                    await logger.adebug("Ban não encontrado (já foi removido)", user_id=user_id)
                except discord.Forbidden:
                    await logger.awarning("Sem permissão para desbanir", user_id=user_id, guild=guild.name)
                
            except Exception as e:
                await logger.aerror("Erro ao processar ban expirado", ban_id=ban.get('id'), error=str(e))
    
    @tasks.loop(hours=24)
    async def cleanup_old_data(self):
        """Limpa dados antigos do banco de dados."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Limpar infrações antigas inativas
            if self.db.db_type == "sqlite":
                await self.db.conn.execute(
                    """DELETE FROM infractions 
                       WHERE active = 0 AND created_at < ?""",
                    (cutoff_date,)
                )
                
                # Limpar eventos de automod antigos
                await self.db.conn.execute(
                    """DELETE FROM automod_events WHERE created_at < ?""",
                    (cutoff_date,)
                )
                
                await self.db.conn.commit()
            else:
                await self.db.conn.execute(
                    """DELETE FROM infractions 
                       WHERE active = false AND created_at < $1""",
                    cutoff_date
                )
                
                await self.db.conn.execute(
                    """DELETE FROM automod_events WHERE created_at < $1""",
                    cutoff_date
                )
            
            await logger.ainfo("Limpeza de dados antigos concluída", cutoff_date=str(cutoff_date))
            
        except Exception as e:
            await logger.aerror("Erro ao limpar dados antigos", error=str(e))
    
    @cleanup_old_data.before_loop
    async def before_cleanup(self):
        """Aguarda o bot estar pronto antes de iniciar."""
        await self.bot.wait_until_ready()
        await logger.ainfo("Scheduler de limpeza iniciado")
    
    async def schedule_mute_expiration(
        self,
        guild_id: int,
        user_id: int,
        expires_at: datetime
    ):
        """
        Agenda a expiração de um mute.
        
        Args:
            guild_id: ID da guild
            user_id: ID do usuário
            expires_at: Data/hora de expiração
        """
        # O sistema de loop tasks já cuida disso automaticamente
        # Esta função existe para compatibilidade futura
        await logger.adebug(
            "Mute agendado para expiração",
            user_id=user_id,
            guild_id=guild_id,
            expires_at=str(expires_at)
        )
    
    async def schedule_ban_expiration(
        self,
        guild_id: int,
        user_id: int,
        expires_at: datetime
    ):
        """
        Agenda a expiração de um ban temporário.
        
        Args:
            guild_id: ID da guild
            user_id: ID do usuário
            expires_at: Data/hora de expiração
        """
        await logger.adebug(
            "Ban temporário agendado para expiração",
            user_id=user_id,
            guild_id=guild_id,
            expires_at=str(expires_at)
        )


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Converte string de duração para timedelta.
    
    Formatos aceitos:
    - 10s, 10sec, 10seconds
    - 5m, 5min, 5minutes
    - 2h, 2hour, 2hours
    - 1d, 1day, 1days
    - 1w, 1week, 1weeks
    
    Args:
        duration_str: String de duração
    
    Returns:
        timedelta ou None se inválido
    """
    import re
    
    duration_str = duration_str.lower().strip()
    
    # Regex para extrair número e unidade
    match = re.match(r'^(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hour|hours?|d|day|days?|w|week|weeks?)$', duration_str)
    
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    # Mapear unidades para segundos
    if unit in ['s', 'sec', 'second', 'seconds']:
        return timedelta(seconds=amount)
    elif unit in ['m', 'min', 'minute', 'minutes']:
        return timedelta(minutes=amount)
    elif unit in ['h', 'hour', 'hours']:
        return timedelta(hours=amount)
    elif unit in ['d', 'day', 'days']:
        return timedelta(days=amount)
    elif unit in ['w', 'week', 'weeks']:
        return timedelta(weeks=amount)
    
    return None


def format_duration(td: timedelta) -> str:
    """
    Formata um timedelta para string legível.
    
    Args:
        td: timedelta
    
    Returns:
        String formatada (ex: "2 dias, 3 horas")
    """
    total_seconds = int(td.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    
    if days > 0:
        parts.append(f"{days} dia{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
    if seconds > 0 and not parts:  # Só mostrar segundos se não houver unidades maiores
        parts.append(f"{seconds} segundo{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts) if parts else "0 segundos"
