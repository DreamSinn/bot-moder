"""
Cog de comandos de moderação.
Implementa todos os comandos básicos e avançados de moderação.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import structlog

from utils import (
    can_execute_action,
    get_mute_role,
    parse_duration,
    format_duration,
    HierarchyError,
    PermissionError
)
from utils.embeds import (
    moderation_action_embed,
    success_embed,
    error_embed,
    infraction_list_embed,
    info_embed
)
from utils.errors import safe_send

logger = structlog.get_logger()


class ModerationCog(commands.Cog, name="Moderação"):
    """Comandos de moderação do servidor."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ban", description="Bane um usuário do servidor")
    @app_commands.describe(
        user="Usuário a ser banido",
        reason="Motivo do banimento",
        delete_messages="Deletar mensagens dos últimos X dias (0-7)"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "Não especificado",
        delete_messages: Optional[int] = 0
    ):
        """Bane um usuário permanentemente."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Obter configuração
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            # Verificar permissões e hierarquia
            await can_execute_action(
                'ban',
                interaction.user,
                user,
                config,
                self.bot.super_admin_ids
            )
            
            # Registrar no banco de dados
            infraction_id = await self.bot.db.add_infraction(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                'ban',
                reason
            )
            
            # Tentar enviar DM ao usuário
            if config.get('messages', {}).get('dm_on_action', True):
                try:
                    dm_embed = error_embed(
                        f"Você foi banido de {interaction.guild.name}",
                        f"**Motivo:** {reason}\n\n"
                        f"**ID da Infração:** {infraction_id}"
                    )
                    
                    if config.get('messages', {}).get('include_appeal_info', True):
                        dm_embed.add_field(
                            name="📨 Apelação",
                            value="Você pode apelar este banimento entrando em contato com a administração do servidor.",
                            inline=False
                        )
                    
                    await safe_send(user, embed=dm_embed)
                except:
                    pass
            
            # Executar o ban
            delete_days = max(0, min(7, delete_messages))
            await interaction.guild.ban(
                user,
                reason=f"{reason} | Moderador: {interaction.user}",
                delete_message_days=delete_days
            )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'ban',
                user.id,
                reason,
                {'delete_days': delete_days}
            )
            
            # Responder ao moderador
            embed = success_embed(
                "✅ Usuário Banido",
                f"{user.mention} foi banido com sucesso.\n**Motivo:** {reason}"
            )
            embed.set_footer(text=f"ID da Infração: {infraction_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário banido",
                user=str(user),
                moderator=str(interaction.user),
                guild=interaction.guild.name,
                reason=reason
            )
            
        except (HierarchyError, PermissionError) as e:
            embed = error_embed("Erro", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao banir usuário", error=str(e))
            raise
    
    @app_commands.command(name="tempban", description="Bane um usuário temporariamente")
    @app_commands.describe(
        user="Usuário a ser banido",
        duration="Duração do ban (ex: 1d, 12h, 30m)",
        reason="Motivo do banimento"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def tempban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: Optional[str] = "Não especificado"
    ):
        """Bane um usuário temporariamente."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse da duração
            duration_td = parse_duration(duration)
            if not duration_td:
                embed = error_embed("Erro", "Duração inválida. Use formatos como: 1d, 12h, 30m")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            expires_at = datetime.utcnow() + duration_td
            
            # Obter configuração
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            # Verificar permissões
            await can_execute_action(
                'ban',
                interaction.user,
                user,
                config,
                self.bot.super_admin_ids
            )
            
            # Registrar no banco de dados
            infraction_id = await self.bot.db.add_infraction(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                'tempban',
                reason,
                expires_at
            )
            
            # Tentar enviar DM
            if config.get('messages', {}).get('dm_on_action', True):
                try:
                    dm_embed = error_embed(
                        f"Você foi banido temporariamente de {interaction.guild.name}",
                        f"**Motivo:** {reason}\n"
                        f"**Duração:** {format_duration(duration_td)}\n"
                        f"**Expira em:** {discord.utils.format_dt(expires_at, 'F')}"
                    )
                    await safe_send(user, embed=dm_embed)
                except:
                    pass
            
            # Executar o ban
            await interaction.guild.ban(
                user,
                reason=f"[TEMPBAN] {reason} | Duração: {format_duration(duration_td)} | Moderador: {interaction.user}"
            )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'tempban',
                user.id,
                reason,
                {'duration': str(duration_td), 'expires_at': str(expires_at)}
            )
            
            # Agendar unban
            await self.bot.scheduler.schedule_ban_expiration(
                interaction.guild.id,
                user.id,
                expires_at
            )
            
            # Responder
            embed = success_embed(
                "✅ Usuário Banido Temporariamente",
                f"{user.mention} foi banido por **{format_duration(duration_td)}**.\n"
                f"**Motivo:** {reason}\n"
                f"**Expira em:** {discord.utils.format_dt(expires_at, 'R')}"
            )
            embed.set_footer(text=f"ID da Infração: {infraction_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário banido temporariamente",
                user=str(user),
                moderator=str(interaction.user),
                duration=str(duration_td)
            )
            
        except (HierarchyError, PermissionError) as e:
            embed = error_embed("Erro", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao banir temporariamente", error=str(e))
            raise
    
    @app_commands.command(name="unban", description="Remove o ban de um usuário")
    @app_commands.describe(
        user_id="ID do usuário a ser desbanido",
        reason="Motivo do desbanimento"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: Optional[str] = "Não especificado"
    ):
        """Remove o ban de um usuário."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Converter para int
            try:
                user_id_int = int(user_id)
            except ValueError:
                embed = error_embed("Erro", "ID de usuário inválido.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Buscar usuário
            user = await self.bot.fetch_user(user_id_int)
            
            # Desbanir
            await interaction.guild.unban(
                user,
                reason=f"{reason} | Moderador: {interaction.user}"
            )
            
            # Atualizar banco de dados
            if self.bot.db.db_type == "sqlite":
                await self.bot.db.conn.execute(
                    """UPDATE infractions SET active = 0 
                       WHERE user_id = ? AND guild_id = ? AND type IN ('ban', 'tempban') AND active = 1""",
                    (user_id_int, interaction.guild.id)
                )
                await self.bot.db.conn.commit()
            else:
                await self.bot.db.conn.execute(
                    """UPDATE infractions SET active = false 
                       WHERE user_id = $1 AND guild_id = $2 AND type IN ('ban', 'tempban') AND active = true""",
                    user_id_int, interaction.guild.id
                )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'unban',
                user_id_int,
                reason
            )
            
            # Responder
            embed = success_embed(
                "✅ Usuário Desbanido",
                f"**{user}** (`{user.id}`) foi desbanido.\n**Motivo:** {reason}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário desbanido",
                user_id=user_id_int,
                moderator=str(interaction.user)
            )
            
        except discord.NotFound:
            embed = error_embed("Erro", "Usuário não encontrado ou não está banido.")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao desbanir", error=str(e))
            raise
    
    @app_commands.command(name="kick", description="Expulsa um usuário do servidor")
    @app_commands.describe(
        user="Usuário a ser expulso",
        reason="Motivo da expulsão"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "Não especificado"
    ):
        """Expulsa um usuário do servidor."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            await can_execute_action(
                'kick',
                interaction.user,
                user,
                config,
                self.bot.super_admin_ids
            )
            
            # Registrar infração
            infraction_id = await self.bot.db.add_infraction(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                'kick',
                reason
            )
            
            # Tentar enviar DM
            if config.get('messages', {}).get('dm_on_action', True):
                try:
                    dm_embed = error_embed(
                        f"Você foi expulso de {interaction.guild.name}",
                        f"**Motivo:** {reason}"
                    )
                    await safe_send(user, embed=dm_embed)
                except:
                    pass
            
            # Executar kick
            await interaction.guild.kick(
                user,
                reason=f"{reason} | Moderador: {interaction.user}"
            )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'kick',
                user.id,
                reason
            )
            
            # Responder
            embed = success_embed(
                "✅ Usuário Expulso",
                f"{user.mention} foi expulso do servidor.\n**Motivo:** {reason}"
            )
            embed.set_footer(text=f"ID da Infração: {infraction_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário expulso",
                user=str(user),
                moderator=str(interaction.user),
                reason=reason
            )
            
        except (HierarchyError, PermissionError) as e:
            embed = error_embed("Erro", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao expulsar", error=str(e))
            raise
    
    @app_commands.command(name="mute", description="Silencia um usuário")
    @app_commands.describe(
        user="Usuário a ser silenciado",
        duration="Duração do mute (ex: 1h, 30m)",
        reason="Motivo do silenciamento"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: Optional[str] = "Não especificado"
    ):
        """Silencia um usuário por um período."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse da duração
            duration_td = parse_duration(duration)
            if not duration_td:
                embed = error_embed("Erro", "Duração inválida. Use formatos como: 1h, 30m, 1d")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            expires_at = datetime.utcnow() + duration_td
            
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            await can_execute_action(
                'mute',
                interaction.user,
                user,
                config,
                self.bot.super_admin_ids
            )
            
            # Obter ou criar cargo de mute
            mute_role = await get_mute_role(interaction.guild)
            
            # Adicionar cargo
            await user.add_roles(mute_role, reason=f"{reason} | Moderador: {interaction.user}")
            
            # Registrar no banco
            await self.bot.db.add_mute(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                reason,
                expires_at
            )
            
            infraction_id = await self.bot.db.add_infraction(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                'mute',
                reason,
                expires_at
            )
            
            # Tentar enviar DM
            if config.get('messages', {}).get('dm_on_action', True):
                try:
                    dm_embed = error_embed(
                        f"Você foi silenciado em {interaction.guild.name}",
                        f"**Motivo:** {reason}\n"
                        f"**Duração:** {format_duration(duration_td)}\n"
                        f"**Expira em:** {discord.utils.format_dt(expires_at, 'F')}"
                    )
                    await safe_send(user, embed=dm_embed)
                except:
                    pass
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'mute',
                user.id,
                reason,
                {'duration': str(duration_td), 'expires_at': str(expires_at)}
            )
            
            # Agendar unmute
            await self.bot.scheduler.schedule_mute_expiration(
                interaction.guild.id,
                user.id,
                expires_at
            )
            
            # Responder
            embed = success_embed(
                "🔇 Usuário Silenciado",
                f"{user.mention} foi silenciado por **{format_duration(duration_td)}**.\n"
                f"**Motivo:** {reason}\n"
                f"**Expira em:** {discord.utils.format_dt(expires_at, 'R')}"
            )
            embed.set_footer(text=f"ID da Infração: {infraction_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário silenciado",
                user=str(user),
                moderator=str(interaction.user),
                duration=str(duration_td)
            )
            
        except (HierarchyError, PermissionError) as e:
            embed = error_embed("Erro", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao silenciar", error=str(e))
            raise
    
    @app_commands.command(name="unmute", description="Remove o silenciamento de um usuário")
    @app_commands.describe(
        user="Usuário a ser dessilenciado",
        reason="Motivo"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "Não especificado"
    ):
        """Remove o silenciamento de um usuário."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Obter cargo de mute
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            
            if not mute_role or mute_role not in user.roles:
                embed = error_embed("Erro", "Este usuário não está silenciado.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Remover cargo
            await user.remove_roles(mute_role, reason=f"{reason} | Moderador: {interaction.user}")
            
            # Atualizar banco
            await self.bot.db.remove_mute(user.id, interaction.guild.id)
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'unmute',
                user.id,
                reason
            )
            
            # Responder
            embed = success_embed(
                "🔊 Usuário Dessilenciado",
                f"{user.mention} pode voltar a enviar mensagens.\n**Motivo:** {reason}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Usuário dessilenciado",
                user=str(user),
                moderator=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao dessilenciar", error=str(e))
            raise
    
    @app_commands.command(name="warn", description="Adverte um usuário")
    @app_commands.describe(
        user="Usuário a ser advertido",
        reason="Motivo da advertência"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        """Adverte um usuário."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            await can_execute_action(
                'warn',
                interaction.user,
                user,
                config,
                self.bot.super_admin_ids
            )
            
            # Registrar advertência
            infraction_id = await self.bot.db.add_infraction(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                'warn',
                reason
            )
            
            # Contar infrações
            infraction_count = await self.bot.db.count_infractions(
                user.id,
                interaction.guild.id,
                days=30
            )
            
            # Verificar escalonamento
            escalation_config = config.get('escalation', {})
            if escalation_config.get('enabled', True):
                # TODO: Implementar ação de escalonamento automático
                pass
            
            # Tentar enviar DM
            if config.get('messages', {}).get('dm_on_action', True):
                try:
                    dm_embed = error_embed(
                        f"Você recebeu uma advertência em {interaction.guild.name}",
                        f"**Motivo:** {reason}\n"
                        f"**Total de advertências (30 dias):** {infraction_count}"
                    )
                    await safe_send(user, embed=dm_embed)
                except:
                    pass
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'warn',
                user.id,
                reason
            )
            
            # Responder
            embed = success_embed(
                "⚠️ Advertência Aplicada",
                f"{user.mention} foi advertido.\n"
                f"**Motivo:** {reason}\n"
                f"**Total de infrações (30 dias):** {infraction_count}"
            )
            embed.set_footer(text=f"ID da Infração: {infraction_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Advertência aplicada",
                user=str(user),
                moderator=str(interaction.user),
                reason=reason,
                total_infractions=infraction_count
            )
            
        except (HierarchyError, PermissionError) as e:
            embed = error_embed("Erro", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await logger.aerror("Erro ao advertir", error=str(e))
            raise
    
    @app_commands.command(name="infractions", description="Lista as infrações de um usuário")
    @app_commands.describe(user="Usuário para verificar")
    @app_commands.checks.has_permissions(kick_members=True)
    async def infractions(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Lista as infrações de um usuário."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            infractions = await self.bot.db.get_infractions(
                user.id,
                interaction.guild.id
            )
            
            embed = infraction_list_embed(user, infractions)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await logger.aerror("Erro ao listar infrações", error=str(e))
            raise
    
    @app_commands.command(name="purge", description="Deleta múltiplas mensagens")
    @app_commands.describe(
        amount="Quantidade de mensagens a deletar (1-100)",
        user="Deletar apenas mensagens deste usuário (opcional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        """Deleta múltiplas mensagens de um canal."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if amount < 1 or amount > 100:
                embed = error_embed("Erro", "A quantidade deve estar entre 1 e 100.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Deletar mensagens
            def check(m):
                if user:
                    return m.author.id == user.id
                return True
            
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'purge',
                user.id if user else None,
                f"Deletadas {len(deleted)} mensagens",
                {'amount': len(deleted), 'channel': interaction.channel.name}
            )
            
            # Responder
            embed = success_embed(
                "🗑️ Mensagens Deletadas",
                f"**{len(deleted)}** mensagens foram deletadas{f' de {user.mention}' if user else ''}."
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Mensagens purgadas",
                amount=len(deleted),
                moderator=str(interaction.user),
                channel=interaction.channel.name,
                target_user=str(user) if user else None
            )
            
        except Exception as e:
            await logger.aerror("Erro ao purgar mensagens", error=str(e))
            raise


async def setup(bot):
    """Registra o cog no bot."""
    await bot.add_cog(ModerationCog(bot))
