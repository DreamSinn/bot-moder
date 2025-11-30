"""
Sistema centralizado de tratamento de erros.
Gerencia exceções e fornece mensagens amigáveis aos usuários.
"""

import discord
from discord.ext import commands
from discord import app_commands
import traceback
import sys
from typing import Optional
import structlog

from .embeds import error_embed

logger = structlog.get_logger()


class ModBotException(Exception):
    """Exceção base para o bot."""
    pass


class PermissionError(ModBotException):
    """Erro de permissões."""
    pass


class HierarchyError(ModBotException):
    """Erro de hierarquia de cargos."""
    pass


class ConfigurationError(ModBotException):
    """Erro de configuração."""
    pass


class DatabaseError(ModBotException):
    """Erro de banco de dados."""
    pass


async def handle_command_error(
    interaction: discord.Interaction,
    error: Exception,
    alert_channel: Optional[discord.TextChannel] = None
):
    """
    Manipula erros de comandos de forma centralizada.
    
    Args:
        interaction: A interação do Discord
        error: O erro que ocorreu
        alert_channel: Canal para enviar alertas críticos
    """
    
    # Extrair o erro original se for um CommandInvokeError
    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original
    
    # Log do erro
    await logger.aerror(
        "Erro no comando",
        command=interaction.command.name if interaction.command else "unknown",
        user=str(interaction.user),
        guild=str(interaction.guild),
        error=str(error),
        error_type=type(error).__name__
    )
    
    # Mensagem padrão para o usuário
    user_message = "Ocorreu um erro ao executar este comando."
    
    # Tratar diferentes tipos de erros
    if isinstance(error, app_commands.MissingPermissions):
        user_message = f"❌ Você não tem permissão para usar este comando.\n\n**Permissões necessárias:** {', '.join(error.missing_permissions)}"
    
    elif isinstance(error, app_commands.BotMissingPermissions):
        user_message = f"❌ Eu não tenho permissões suficientes para executar esta ação.\n\n**Permissões necessárias:** {', '.join(error.missing_permissions)}"
    
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_message = f"⏱️ Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos."
    
    elif isinstance(error, app_commands.NoPrivateMessage):
        user_message = "❌ Este comando não pode ser usado em mensagens privadas."
    
    elif isinstance(error, HierarchyError):
        user_message = f"❌ Erro de hierarquia: {str(error)}"
    
    elif isinstance(error, PermissionError):
        user_message = f"❌ Erro de permissão: {str(error)}"
    
    elif isinstance(error, ConfigurationError):
        user_message = f"⚙️ Erro de configuração: {str(error)}"
    
    elif isinstance(error, DatabaseError):
        user_message = "❌ Erro ao acessar o banco de dados. Tente novamente em alguns instantes."
    
    elif isinstance(error, discord.Forbidden):
        user_message = "❌ Não tenho permissão para executar esta ação. Verifique minhas permissões no servidor."
    
    elif isinstance(error, discord.NotFound):
        user_message = "❌ Recurso não encontrado. O usuário, canal ou mensagem pode ter sido deletado."
    
    elif isinstance(error, discord.HTTPException):
        if error.status == 429:
            user_message = "⏱️ Rate limit atingido. Aguarde alguns segundos e tente novamente."
        else:
            user_message = f"❌ Erro de comunicação com o Discord: {error.text}"
    
    elif isinstance(error, ValueError):
        user_message = f"❌ Valor inválido: {str(error)}"
    
    else:
        # Erro desconhecido - enviar alerta
        user_message = "❌ Ocorreu um erro inesperado. A equipe foi notificada."
        
        # Enviar alerta para canal de administração
        if alert_channel:
            try:
                error_details = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                
                alert_embed = discord.Embed(
                    title="🚨 Erro Crítico Detectado",
                    color=0xe74c3c,
                    description=f"**Comando:** {interaction.command.name if interaction.command else 'unknown'}\n"
                                f"**Usuário:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                                f"**Guild:** {interaction.guild.name if interaction.guild else 'DM'} (`{interaction.guild.id if interaction.guild else 'N/A'}`)"
                )
                
                # Truncar traceback se for muito longo
                if len(error_details) > 1000:
                    error_details = error_details[-1000:]
                
                alert_embed.add_field(
                    name="📋 Traceback",
                    value=f"```python\n{error_details}\n```",
                    inline=False
                )
                
                await alert_channel.send(embed=alert_embed)
            except Exception as e:
                await logger.aerror("Erro ao enviar alerta", error=str(e))
    
    # Enviar mensagem de erro para o usuário
    embed = error_embed("Erro", user_message)
    
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await logger.aerror("Erro ao enviar mensagem de erro", error=str(e))


class ErrorHandler:
    """Classe para gerenciar tratamento de erros do bot."""
    
    def __init__(self, bot: commands.Bot, alert_channel_id: Optional[int] = None):
        self.bot = bot
        self.alert_channel_id = alert_channel_id
        self.alert_channel: Optional[discord.TextChannel] = None
    
    async def setup(self):
        """Configura o handler de erros."""
        if self.alert_channel_id:
            self.alert_channel = self.bot.get_channel(self.alert_channel_id)
            if not self.alert_channel:
                await logger.awarning("Canal de alertas não encontrado", channel_id=self.alert_channel_id)
        
        # Registrar handler global de erros de app commands
        @self.bot.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await handle_command_error(interaction, error, self.alert_channel)
    
    async def handle_task_error(self, task_name: str, error: Exception):
        """Manipula erros de tarefas assíncronas."""
        await logger.aerror(
            "Erro em tarefa assíncrona",
            task=task_name,
            error=str(error),
            error_type=type(error).__name__
        )
        
        if self.alert_channel:
            try:
                error_details = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                
                alert_embed = discord.Embed(
                    title="🚨 Erro em Tarefa Assíncrona",
                    color=0xe74c3c,
                    description=f"**Tarefa:** {task_name}"
                )
                
                if len(error_details) > 1000:
                    error_details = error_details[-1000:]
                
                alert_embed.add_field(
                    name="📋 Traceback",
                    value=f"```python\n{error_details}\n```",
                    inline=False
                )
                
                await self.alert_channel.send(embed=alert_embed)
            except Exception as e:
                await logger.aerror("Erro ao enviar alerta de tarefa", error=str(e))


async def safe_send(
    destination: discord.abc.Messageable,
    content: str = None,
    embed: discord.Embed = None,
    **kwargs
) -> Optional[discord.Message]:
    """
    Envia uma mensagem com tratamento de erros.
    
    Args:
        destination: Canal ou usuário para enviar
        content: Conteúdo da mensagem
        embed: Embed para enviar
        **kwargs: Argumentos adicionais
    
    Returns:
        A mensagem enviada ou None se falhar
    """
    try:
        return await destination.send(content=content, embed=embed, **kwargs)
    except discord.Forbidden:
        await logger.awarning("Sem permissão para enviar mensagem", destination=str(destination))
    except discord.HTTPException as e:
        await logger.aerror("Erro HTTP ao enviar mensagem", error=str(e))
    except Exception as e:
        await logger.aerror("Erro ao enviar mensagem", error=str(e))
    
    return None


async def safe_delete(message: discord.Message, delay: float = 0) -> bool:
    """
    Deleta uma mensagem com tratamento de erros.
    
    Args:
        message: Mensagem para deletar
        delay: Delay antes de deletar (em segundos)
    
    Returns:
        True se deletou com sucesso, False caso contrário
    """
    try:
        await message.delete(delay=delay)
        return True
    except discord.NotFound:
        await logger.adebug("Mensagem já foi deletada")
    except discord.Forbidden:
        await logger.awarning("Sem permissão para deletar mensagem")
    except Exception as e:
        await logger.aerror("Erro ao deletar mensagem", error=str(e))
    
    return False


async def safe_edit(
    message: discord.Message,
    content: str = None,
    embed: discord.Embed = None,
    **kwargs
) -> bool:
    """
    Edita uma mensagem com tratamento de erros.
    
    Args:
        message: Mensagem para editar
        content: Novo conteúdo
        embed: Novo embed
        **kwargs: Argumentos adicionais
    
    Returns:
        True se editou com sucesso, False caso contrário
    """
    try:
        await message.edit(content=content, embed=embed, **kwargs)
        return True
    except discord.NotFound:
        await logger.adebug("Mensagem não encontrada para editar")
    except discord.Forbidden:
        await logger.awarning("Sem permissão para editar mensagem")
    except Exception as e:
        await logger.aerror("Erro ao editar mensagem", error=str(e))
    
    return False
