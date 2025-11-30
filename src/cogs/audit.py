"""
Cog de auditoria e logs.
Registra e exibe logs de todas as ações de moderação e eventos do servidor.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import structlog

from utils.embeds import log_embed, info_embed
from utils.errors import safe_send

logger = structlog.get_logger()


class AuditCog(commands.Cog, name="Auditoria"):
    """Sistema de logs e auditoria."""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_log(
        self,
        guild: discord.Guild,
        embed: discord.Embed
    ):
        """Envia um log para o canal configurado."""
        try:
            config = await self.bot.get_guild_config(guild.id)
            log_config = config.get('logging', {})
            
            if not log_config.get('enabled', True):
                return
            
            log_channel_id = log_config.get('log_channel_id')
            if not log_channel_id:
                return
            
            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                await logger.awarning("Canal de logs não encontrado", guild=guild.name)
                return
            
            await safe_send(log_channel, embed=embed)
            
        except Exception as e:
            await logger.aerror("Erro ao enviar log", error=str(e))
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Registra banimentos."""
        try:
            config = await self.bot.get_guild_config(guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            # Buscar informações do audit log
            moderator = None
            reason = "Não especificado"
            
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                    if entry.target.id == user.id:
                        moderator = entry.user
                        reason = entry.reason or "Não especificado"
                        break
            except:
                pass
            
            if not moderator:
                moderator = guild.me
            
            embed = log_embed(
                "BAN",
                moderator,
                user,
                reason
            )
            
            await self.send_log(guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar ban", error=str(e))
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Registra desbanimentos."""
        try:
            config = await self.bot.get_guild_config(guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            moderator = None
            reason = "Não especificado"
            
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                    if entry.target.id == user.id:
                        moderator = entry.user
                        reason = entry.reason or "Não especificado"
                        break
            except:
                pass
            
            if not moderator:
                moderator = guild.me
            
            embed = log_embed(
                "UNBAN",
                moderator,
                user,
                reason
            )
            
            await self.send_log(guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar unban", error=str(e))
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Registra kicks e saídas."""
        try:
            config = await self.bot.get_guild_config(member.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            # Verificar se foi kick
            is_kick = False
            moderator = None
            reason = "Não especificado"
            
            try:
                async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                    if entry.target.id == member.id:
                        is_kick = True
                        moderator = entry.user
                        reason = entry.reason or "Não especificado"
                        break
            except:
                pass
            
            if is_kick and moderator:
                embed = log_embed(
                    "KICK",
                    moderator,
                    member,
                    reason
                )
                await self.send_log(member.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar kick", error=str(e))
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Registra mudanças em membros (mutes via timeout)."""
        try:
            config = await self.bot.get_guild_config(after.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            # Verificar timeout (mute nativo do Discord)
            if before.timed_out_until != after.timed_out_until:
                if after.timed_out_until:
                    # Membro foi mutado
                    moderator = None
                    reason = "Não especificado"
                    
                    try:
                        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                            if entry.target.id == after.id:
                                moderator = entry.user
                                reason = entry.reason or "Não especificado"
                                break
                    except:
                        pass
                    
                    if moderator:
                        embed = log_embed(
                            "TIMEOUT",
                            moderator,
                            after,
                            reason,
                            {"Expira em": discord.utils.format_dt(after.timed_out_until, 'R')}
                        )
                        await self.send_log(after.guild, embed)
                else:
                    # Timeout removido
                    moderator = None
                    
                    try:
                        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                            if entry.target.id == after.id:
                                moderator = entry.user
                                break
                    except:
                        pass
                    
                    if moderator:
                        embed = log_embed(
                            "TIMEOUT REMOVIDO",
                            moderator,
                            after
                        )
                        await self.send_log(after.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar member update", error=str(e))
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Registra mensagens deletadas."""
        if not message.guild or message.author.bot:
            return
        
        try:
            config = await self.bot.get_guild_config(message.guild.id)
            if not config.get('logging', {}).get('log_deletes', False):
                return
            
            embed = discord.Embed(
                title="🗑️ Mensagem Deletada",
                color=0xe74c3c,
                timestamp=message.created_at
            )
            
            embed.add_field(name="Autor", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
            embed.add_field(name="Canal", value=message.channel.mention, inline=True)
            
            if message.content:
                content = message.content[:1000]
                embed.add_field(name="Conteúdo", value=content, inline=False)
            
            if message.attachments:
                attachments_info = "\n".join([f"• {att.filename}" for att in message.attachments])
                embed.add_field(name="Anexos", value=attachments_info, inline=False)
            
            await self.send_log(message.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar message delete", error=str(e))
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Registra mensagens editadas."""
        if not after.guild or after.author.bot:
            return
        
        if before.content == after.content:
            return
        
        try:
            config = await self.bot.get_guild_config(after.guild.id)
            if not config.get('logging', {}).get('log_edits', False):
                return
            
            embed = discord.Embed(
                title="✏️ Mensagem Editada",
                color=0xf39c12,
                timestamp=after.edited_at or after.created_at
            )
            
            embed.add_field(name="Autor", value=f"{after.author.mention} (`{after.author.id}`)", inline=True)
            embed.add_field(name="Canal", value=after.channel.mention, inline=True)
            
            if before.content:
                before_content = before.content[:500]
                embed.add_field(name="Antes", value=before_content, inline=False)
            
            if after.content:
                after_content = after.content[:500]
                embed.add_field(name="Depois", value=after_content, inline=False)
            
            embed.add_field(name="Link", value=f"[Ir para mensagem]({after.jump_url})", inline=False)
            
            await self.send_log(after.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar message edit", error=str(e))
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Registra criação de canais."""
        try:
            config = await self.bot.get_guild_config(channel.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            moderator = None
            
            try:
                async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                    if entry.target.id == channel.id:
                        moderator = entry.user
                        break
            except:
                pass
            
            if moderator:
                embed = discord.Embed(
                    title="➕ Canal Criado",
                    color=0x2ecc71,
                    description=f"**Canal:** {channel.mention}\n**Tipo:** {channel.type}"
                )
                embed.add_field(name="Criado por", value=moderator.mention, inline=True)
                
                await self.send_log(channel.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar channel create", error=str(e))
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Registra deleção de canais."""
        try:
            config = await self.bot.get_guild_config(channel.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            moderator = None
            
            try:
                async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                    if entry.target.id == channel.id:
                        moderator = entry.user
                        break
            except:
                pass
            
            if moderator:
                embed = discord.Embed(
                    title="➖ Canal Deletado",
                    color=0xe74c3c,
                    description=f"**Canal:** {channel.name}\n**Tipo:** {channel.type}"
                )
                embed.add_field(name="Deletado por", value=moderator.mention, inline=True)
                
                await self.send_log(channel.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar channel delete", error=str(e))
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Registra criação de cargos."""
        try:
            config = await self.bot.get_guild_config(role.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            moderator = None
            
            try:
                async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                    if entry.target.id == role.id:
                        moderator = entry.user
                        break
            except:
                pass
            
            if moderator:
                embed = discord.Embed(
                    title="➕ Cargo Criado",
                    color=0x2ecc71,
                    description=f"**Cargo:** {role.mention}\n**Cor:** {role.color}"
                )
                embed.add_field(name="Criado por", value=moderator.mention, inline=True)
                
                await self.send_log(role.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar role create", error=str(e))
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Registra deleção de cargos."""
        try:
            config = await self.bot.get_guild_config(role.guild.id)
            if not config.get('logging', {}).get('log_actions', True):
                return
            
            moderator = None
            
            try:
                async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                    if entry.target.id == role.id:
                        moderator = entry.user
                        break
            except:
                pass
            
            if moderator:
                embed = discord.Embed(
                    title="➖ Cargo Deletado",
                    color=0xe74c3c,
                    description=f"**Cargo:** {role.name}"
                )
                embed.add_field(name="Deletado por", value=moderator.mention, inline=True)
                
                await self.send_log(role.guild, embed)
            
        except Exception as e:
            await logger.aerror("Erro ao registrar role delete", error=str(e))
    
    @app_commands.command(name="logs", description="Exporta logs de moderação")
    @app_commands.describe(
        limit="Quantidade de ações para exportar (padrão: 100)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def export_logs(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 100
    ):
        """Exporta logs de moderação para arquivo."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if limit < 1 or limit > 1000:
                limit = 100
            
            # Buscar ações do banco
            if self.bot.db.db_type == "sqlite":
                async with self.bot.db.conn.execute(
                    """SELECT * FROM mod_actions 
                       WHERE guild_id = ? 
                       ORDER BY created_at DESC 
                       LIMIT ?""",
                    (interaction.guild.id, limit)
                ) as cursor:
                    actions = await cursor.fetchall()
                    actions = [dict(row) for row in actions]
            else:
                actions = await self.bot.db.conn.fetch(
                    """SELECT * FROM mod_actions 
                       WHERE guild_id = $1 
                       ORDER BY created_at DESC 
                       LIMIT $2""",
                    interaction.guild.id, limit
                )
                actions = [dict(row) for row in actions]
            
            if not actions:
                embed = info_embed("Sem Logs", "Não há logs de moderação registrados.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Criar arquivo de texto
            import io
            
            output = io.StringIO()
            output.write(f"LOGS DE MODERAÇÃO - {interaction.guild.name}\n")
            output.write(f"Exportado em: {discord.utils.format_dt(discord.utils.utcnow(), 'F')}\n")
            output.write(f"Total de ações: {len(actions)}\n")
            output.write("=" * 80 + "\n\n")
            
            for action in actions:
                output.write(f"ID: {action.get('id')}\n")
                output.write(f"Tipo: {action.get('action_type')}\n")
                output.write(f"Moderador ID: {action.get('moderator_id')}\n")
                output.write(f"Alvo ID: {action.get('target_id')}\n")
                output.write(f"Motivo: {action.get('reason', 'N/A')}\n")
                output.write(f"Data: {action.get('created_at')}\n")
                output.write("-" * 80 + "\n")
            
            output.seek(0)
            
            file = discord.File(
                fp=io.BytesIO(output.getvalue().encode('utf-8')),
                filename=f"logs_{interaction.guild.id}.txt"
            )
            
            embed = info_embed(
                "📋 Logs Exportados",
                f"**{len(actions)}** ações de moderação foram exportadas."
            )
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            
            await logger.ainfo(
                "Logs exportados",
                moderator=str(interaction.user),
                guild=interaction.guild.name,
                count=len(actions)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao exportar logs", error=str(e))
            raise


async def setup(bot):
    """Registra o cog no bot."""
    await bot.add_cog(AuditCog(bot))
