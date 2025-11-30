"""
Cog de configuração.
Permite aos administradores configurar o bot e suas funcionalidades.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import structlog

from utils.embeds import success_embed, error_embed, config_embed, info_embed, appeal_embed
from utils.permissions import is_admin

logger = structlog.get_logger()


class ConfigCog(commands.Cog, name="Configuração"):
    """Comandos de configuração do bot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    config_group = app_commands.Group(
        name="config",
        description="Comandos de configuração do bot"
    )
    
    @config_group.command(name="view", description="Visualiza a configuração atual")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_view(self, interaction: discord.Interaction):
        """Mostra a configuração atual do servidor."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            embed = config_embed(config, interaction.guild.name)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await logger.aerror("Erro ao visualizar config", error=str(e))
            raise
    
    @config_group.command(name="logs", description="Configura o canal de logs")
    @app_commands.describe(channel="Canal onde os logs serão enviados")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_logs(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Configura o canal de logs."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'logging' not in config:
                config['logging'] = {}
            
            config['logging']['log_channel_id'] = channel.id
            config['logging']['enabled'] = True
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            embed = success_embed(
                "✅ Canal de Logs Configurado",
                f"Os logs serão enviados para {channel.mention}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Enviar mensagem de teste no canal
            test_embed = info_embed(
                "📝 Canal de Logs Configurado",
                "Este canal foi configurado para receber logs de moderação e eventos do servidor."
            )
            await channel.send(embed=test_embed)
            
            await logger.ainfo(
                "Canal de logs configurado",
                guild=interaction.guild.name,
                channel=channel.name,
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar logs", error=str(e))
            raise
    
    @config_group.command(name="modrole", description="Define o cargo de moderador")
    @app_commands.describe(role="Cargo que terá permissões de moderador")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_modrole(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Define o cargo de moderador."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'permissions' not in config:
                config['permissions'] = {}
            
            config['permissions']['mod_role_id'] = role.id
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            embed = success_embed(
                "✅ Cargo de Moderador Definido",
                f"O cargo {role.mention} foi definido como cargo de moderador."
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Cargo de moderador definido",
                guild=interaction.guild.name,
                role=role.name,
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao definir cargo de moderador", error=str(e))
            raise
    
    @config_group.command(name="automod", description="Ativa/desativa a auto-moderação")
    @app_commands.describe(enabled="Ativar ou desativar")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_automod(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        """Ativa ou desativa a auto-moderação."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'automod' not in config:
                config['automod'] = {}
            
            config['automod']['enabled'] = enabled
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            status = "ativada" if enabled else "desativada"
            embed = success_embed(
                f"✅ Auto-Moderação {status.capitalize()}",
                f"A auto-moderação foi {status} com sucesso."
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Auto-moderação configurada",
                guild=interaction.guild.name,
                enabled=enabled,
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar automod", error=str(e))
            raise
    
    @config_group.command(name="antiraid", description="Configura proteção anti-raid")
    @app_commands.describe(
        enabled="Ativar ou desativar",
        threshold="Número de entradas para disparar alerta",
        time_window="Janela de tempo em segundos"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_antiraid(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        threshold: Optional[int] = 10,
        time_window: Optional[int] = 60
    ):
        """Configura a proteção anti-raid."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'anti_raid' not in config:
                config['anti_raid'] = {}
            
            config['anti_raid']['enabled'] = enabled
            config['anti_raid']['join_threshold'] = threshold
            config['anti_raid']['time_window'] = time_window
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            status = "ativada" if enabled else "desativada"
            embed = success_embed(
                f"✅ Proteção Anti-Raid {status.capitalize()}",
                f"**Status:** {status}\n"
                f"**Threshold:** {threshold} entradas\n"
                f"**Janela de tempo:** {time_window} segundos"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Anti-raid configurado",
                guild=interaction.guild.name,
                enabled=enabled,
                threshold=threshold,
                time_window=time_window,
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar anti-raid", error=str(e))
            raise
    
    @config_group.command(name="antinuke", description="Configura proteção anti-nuke")
    @app_commands.describe(enabled="Ativar ou desativar")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_antinuke(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        """Configura a proteção anti-nuke."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'anti_nuke' not in config:
                config['anti_nuke'] = {}
            
            config['anti_nuke']['enabled'] = enabled
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            status = "ativada" if enabled else "desativada"
            embed = success_embed(
                f"✅ Proteção Anti-Nuke {status.capitalize()}",
                f"A proteção anti-nuke foi {status} com sucesso."
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Anti-nuke configurado",
                guild=interaction.guild.name,
                enabled=enabled,
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar anti-nuke", error=str(e))
            raise
    
    @config_group.command(name="badwords", description="Adiciona palavras à lista de bloqueio")
    @app_commands.describe(words="Palavras separadas por vírgula")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_badwords(
        self,
        interaction: discord.Interaction,
        words: str
    ):
        """Adiciona palavras à lista de bloqueio."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            config = await self.bot.get_guild_config(interaction.guild.id)
            
            if 'automod' not in config:
                config['automod'] = {}
            if 'bad_words' not in config['automod']:
                config['automod']['bad_words'] = {'enabled': True, 'words': [], 'action': 'warn'}
            
            # Adicionar palavras
            new_words = [w.strip() for w in words.split(',') if w.strip()]
            existing_words = config['automod']['bad_words'].get('words', [])
            
            for word in new_words:
                if word not in existing_words:
                    existing_words.append(word)
            
            config['automod']['bad_words']['words'] = existing_words
            
            await self.bot.update_guild_config(interaction.guild.id, config)
            
            embed = success_embed(
                "✅ Palavras Bloqueadas Atualizadas",
                f"**{len(new_words)}** palavras foram adicionadas à lista de bloqueio.\n"
                f"**Total:** {len(existing_words)} palavras"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Palavras bloqueadas atualizadas",
                guild=interaction.guild.name,
                count=len(new_words),
                admin=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar bad words", error=str(e))
            raise
    
    @app_commands.command(name="slowmode", description="Define o modo lento em um canal")
    @app_commands.describe(
        channel="Canal para aplicar slowmode",
        seconds="Segundos de delay (0 para desativar)"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        seconds: int
    ):
        """Define o modo lento em um canal."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if seconds < 0 or seconds > 21600:
                embed = error_embed("Erro", "O valor deve estar entre 0 e 21600 segundos (6 horas).")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            await channel.edit(slowmode_delay=seconds)
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'slowmode',
                None,
                f"Slowmode definido para {seconds}s",
                {'channel': channel.name, 'seconds': seconds}
            )
            
            if seconds == 0:
                embed = success_embed(
                    "✅ Slowmode Desativado",
                    f"O modo lento foi desativado em {channel.mention}"
                )
            else:
                embed = success_embed(
                    "✅ Slowmode Ativado",
                    f"Modo lento de **{seconds}** segundos ativado em {channel.mention}"
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Slowmode configurado",
                guild=interaction.guild.name,
                channel=channel.name,
                seconds=seconds,
                moderator=str(interaction.user)
            )
            
        except Exception as e:
            await logger.aerror("Erro ao configurar slowmode", error=str(e))
            raise
    
    @app_commands.command(name="lock", description="Bloqueia um canal")
    @app_commands.describe(
        channel="Canal para bloquear",
        reason="Motivo do bloqueio"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: Optional[str] = "Não especificado"
    ):
        """Bloqueia um canal impedindo membros de enviar mensagens."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            target_channel = channel or interaction.channel
            
            # Remover permissão de enviar mensagens do @everyone
            await target_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
                reason=f"Canal bloqueado por {interaction.user}: {reason}"
            )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'lock',
                None,
                reason,
                {'channel': target_channel.name}
            )
            
            embed = success_embed(
                "🔒 Canal Bloqueado",
                f"{target_channel.mention} foi bloqueado.\n**Motivo:** {reason}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Enviar mensagem no canal
            lock_embed = info_embed(
                "🔒 Canal Bloqueado",
                f"Este canal foi bloqueado por {interaction.user.mention}.\n**Motivo:** {reason}"
            )
            await target_channel.send(embed=lock_embed)
            
            await logger.ainfo(
                "Canal bloqueado",
                guild=interaction.guild.name,
                channel=target_channel.name,
                moderator=str(interaction.user),
                reason=reason
            )
            
        except Exception as e:
            await logger.aerror("Erro ao bloquear canal", error=str(e))
            raise
    
    @app_commands.command(name="unlock", description="Desbloqueia um canal")
    @app_commands.describe(
        channel="Canal para desbloquear",
        reason="Motivo do desbloqueio"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        reason: Optional[str] = "Não especificado"
    ):
        """Desbloqueia um canal."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            target_channel = channel or interaction.channel
            
            # Restaurar permissão de enviar mensagens do @everyone
            await target_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None,
                reason=f"Canal desbloqueado por {interaction.user}: {reason}"
            )
            
            # Registrar ação
            await self.bot.db.log_action(
                interaction.guild.id,
                interaction.user.id,
                'unlock',
                None,
                reason,
                {'channel': target_channel.name}
            )
            
            embed = success_embed(
                "🔓 Canal Desbloqueado",
                f"{target_channel.mention} foi desbloqueado.\n**Motivo:** {reason}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Enviar mensagem no canal
            unlock_embed = info_embed(
                "🔓 Canal Desbloqueado",
                f"Este canal foi desbloqueado por {interaction.user.mention}.\n**Motivo:** {reason}"
            )
            await target_channel.send(embed=unlock_embed)
            
            await logger.ainfo(
                "Canal desbloqueado",
                guild=interaction.guild.name,
                channel=target_channel.name,
                moderator=str(interaction.user),
                reason=reason
            )
            
        except Exception as e:
            await logger.aerror("Erro ao desbloquear canal", error=str(e))
            raise
    
    @app_commands.command(name="appeal", description="Inicia um processo de apelação")
    @app_commands.describe(
        infraction_id="ID da infração que deseja apelar",
        reason="Motivo da apelação"
    )
    async def appeal(
        self,
        interaction: discord.Interaction,
        infraction_id: int,
        reason: str
    ):
        """Permite que um usuário apele uma infração."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Verificar se a infração existe
            if self.bot.db.db_type == "sqlite":
                async with self.bot.db.conn.execute(
                    "SELECT * FROM infractions WHERE id = ? AND user_id = ?",
                    (infraction_id, interaction.user.id)
                ) as cursor:
                    infraction = await cursor.fetchone()
                    if infraction:
                        infraction = dict(infraction)
            else:
                infraction = await self.bot.db.conn.fetchrow(
                    "SELECT * FROM infractions WHERE id = $1 AND user_id = $2",
                    infraction_id, interaction.user.id
                )
                if infraction:
                    infraction = dict(infraction)
            
            if not infraction:
                embed = error_embed(
                    "Erro",
                    "Infração não encontrada ou você não tem permissão para apelá-la."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Enviar apelação para o canal de logs
            config = await self.bot.get_guild_config(interaction.guild.id)
            log_channel_id = config.get('logging', {}).get('log_channel_id')
            
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    appeal_embed_msg = appeal_embed(
                        interaction.user,
                        infraction_id,
                        reason
                    )
                    await log_channel.send(embed=appeal_embed_msg)
            
            # Confirmar ao usuário
            embed = success_embed(
                "📨 Apelação Enviada",
                f"Sua apelação para a infração **#{infraction_id}** foi enviada à equipe de moderação.\n\n"
                f"**Motivo da apelação:** {reason}\n\n"
                f"Aguarde a análise da equipe."
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await logger.ainfo(
                "Apelação enviada",
                user=str(interaction.user),
                guild=interaction.guild.name,
                infraction_id=infraction_id
            )
            
        except Exception as e:
            await logger.aerror("Erro ao processar apelação", error=str(e))
            raise
    
    @app_commands.command(name="help", description="Mostra ajuda sobre os comandos do bot")
    async def help_command(self, interaction: discord.Interaction):
        """Mostra informações de ajuda."""
        embed = discord.Embed(
            title="📚 Ajuda - Bot de Moderação",
            description="Bot completo de moderação com funcionalidades avançadas.",
            color=0x3498db
        )
        
        embed.add_field(
            name="🔨 Comandos de Moderação",
            value=(
                "`/ban` - Bane um usuário\n"
                "`/tempban` - Ban temporário\n"
                "`/unban` - Remove ban\n"
                "`/kick` - Expulsa usuário\n"
                "`/mute` - Silencia usuário\n"
                "`/unmute` - Remove silenciamento\n"
                "`/warn` - Adverte usuário\n"
                "`/infractions` - Lista infrações\n"
                "`/purge` - Deleta mensagens"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Configuração",
            value=(
                "`/config view` - Ver configuração\n"
                "`/config logs` - Configurar logs\n"
                "`/config modrole` - Definir cargo mod\n"
                "`/config automod` - Ativar/desativar automod\n"
                "`/config antiraid` - Configurar anti-raid\n"
                "`/config antinuke` - Configurar anti-nuke\n"
                "`/config badwords` - Adicionar palavras bloqueadas"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Utilidades",
            value=(
                "`/slowmode` - Modo lento\n"
                "`/lock` - Bloquear canal\n"
                "`/unlock` - Desbloquear canal\n"
                "`/logs` - Exportar logs\n"
                "`/appeal` - Apelar infração"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🤖 Auto-Moderação",
            value=(
                "• Detecção de spam\n"
                "• Bloqueio de links\n"
                "• Bloqueio de convites\n"
                "• Filtro de palavras\n"
                "• Proteção anti-raid\n"
                "• Proteção anti-nuke"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use /config view para ver a configuração atual")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Registra o cog no bot."""
    await bot.add_cog(ConfigCog(bot))
