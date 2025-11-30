"""
Sistema de embeds padronizados para o bot.
Fornece embeds visuais consistentes para todas as ações.
"""

import discord
from datetime import datetime
from typing import Optional


class EmbedColors:
    """Cores padrão para diferentes tipos de embeds."""
    SUCCESS = 0x2ecc71  # Verde
    ERROR = 0xe74c3c    # Vermelho
    WARNING = 0xf39c12  # Laranja
    INFO = 0x3498db     # Azul
    MODERATION = 0x9b59b6  # Roxo
    AUTOMOD = 0xe67e22  # Laranja escuro


def create_base_embed(
    title: str,
    description: str = None,
    color: int = EmbedColors.INFO,
    timestamp: bool = True
) -> discord.Embed:
    """Cria um embed base com configurações padrão."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if timestamp:
        embed.timestamp = datetime.utcnow()
    
    return embed


def success_embed(title: str, description: str = None) -> discord.Embed:
    """Cria um embed de sucesso."""
    return create_base_embed(title, description, EmbedColors.SUCCESS)


def error_embed(title: str, description: str = None) -> discord.Embed:
    """Cria um embed de erro."""
    return create_base_embed(title, description, EmbedColors.ERROR)


def warning_embed(title: str, description: str = None) -> discord.Embed:
    """Cria um embed de aviso."""
    return create_base_embed(title, description, EmbedColors.WARNING)


def info_embed(title: str, description: str = None) -> discord.Embed:
    """Cria um embed informativo."""
    return create_base_embed(title, description, EmbedColors.INFO)


def moderation_action_embed(
    action: str,
    target: discord.Member,
    moderator: discord.Member,
    reason: str = None,
    duration: str = None,
    infraction_id: int = None
) -> discord.Embed:
    """Cria um embed para ações de moderação."""
    embed = discord.Embed(
        title=f"🔨 {action.upper()}",
        color=EmbedColors.MODERATION,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="👤 Usuário", value=f"{target.mention} (`{target.id}`)", inline=True)
    embed.add_field(name="🛡️ Moderador", value=f"{moderator.mention}", inline=True)
    
    if duration:
        embed.add_field(name="⏱️ Duração", value=duration, inline=True)
    
    if reason:
        embed.add_field(name="📝 Motivo", value=reason, inline=False)
    else:
        embed.add_field(name="📝 Motivo", value="Não especificado", inline=False)
    
    if infraction_id:
        embed.set_footer(text=f"ID da Infração: {infraction_id}")
    
    return embed


def automod_embed(
    event_type: str,
    user: discord.Member,
    action: str,
    details: str = None
) -> discord.Embed:
    """Cria um embed para eventos de auto-moderação."""
    embed = discord.Embed(
        title=f"🤖 Auto-Moderação: {event_type}",
        color=EmbedColors.AUTOMOD,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="👤 Usuário", value=f"{user.mention} (`{user.id}`)", inline=True)
    embed.add_field(name="⚡ Ação", value=action, inline=True)
    
    if details:
        embed.add_field(name="📋 Detalhes", value=details, inline=False)
    
    return embed


def infraction_list_embed(
    user: discord.Member,
    infractions: list,
    page: int = 1,
    total_pages: int = 1
) -> discord.Embed:
    """Cria um embed com lista de infrações."""
    embed = discord.Embed(
        title=f"📋 Infrações de {user.name}",
        description=f"Total de infrações: {len(infractions)}",
        color=EmbedColors.INFO,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    
    if not infractions:
        embed.add_field(
            name="✅ Registro Limpo",
            value="Este usuário não possui infrações registradas.",
            inline=False
        )
    else:
        for inf in infractions[:10]:  # Mostrar até 10 por página
            infraction_type = inf.get('type', 'unknown').upper()
            reason = inf.get('reason', 'Não especificado')
            created_at = inf.get('created_at', 'Data desconhecida')
            active = "🟢 Ativa" if inf.get('active', False) else "🔴 Inativa"
            
            embed.add_field(
                name=f"{infraction_type} - ID: {inf.get('id', 'N/A')}",
                value=f"**Motivo:** {reason}\n**Data:** {created_at}\n**Status:** {active}",
                inline=False
            )
    
    if total_pages > 1:
        embed.set_footer(text=f"Página {page}/{total_pages}")
    
    return embed


def log_embed(
    action: str,
    moderator: discord.Member,
    target: Optional[discord.Member] = None,
    reason: str = None,
    additional_info: dict = None
) -> discord.Embed:
    """Cria um embed para logs de auditoria."""
    embed = discord.Embed(
        title=f"📝 Log: {action}",
        color=EmbedColors.MODERATION,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="🛡️ Moderador", value=f"{moderator.mention} (`{moderator.id}`)", inline=True)
    
    if target:
        embed.add_field(name="🎯 Alvo", value=f"{target.mention} (`{target.id}`)", inline=True)
    
    if reason:
        embed.add_field(name="📝 Motivo", value=reason, inline=False)
    
    if additional_info:
        for key, value in additional_info.items():
            embed.add_field(name=key, value=str(value), inline=True)
    
    return embed


def raid_alert_embed(
    join_count: int,
    time_window: int,
    action_taken: str = None
) -> discord.Embed:
    """Cria um embed de alerta de raid."""
    embed = discord.Embed(
        title="🚨 ALERTA DE RAID DETECTADO",
        description=f"**{join_count}** usuários entraram em **{time_window}** segundos!",
        color=EmbedColors.ERROR,
        timestamp=datetime.utcnow()
    )
    
    if action_taken:
        embed.add_field(name="⚡ Ação Tomada", value=action_taken, inline=False)
    
    embed.add_field(
        name="🛡️ Recomendação",
        value="Verifique os novos membros e considere ativar o modo lockdown.",
        inline=False
    )
    
    return embed


def nuke_alert_embed(
    event_type: str,
    count: int,
    actor: Optional[discord.Member] = None
) -> discord.Embed:
    """Cria um embed de alerta de nuke."""
    embed = discord.Embed(
        title="⚠️ ALERTA DE NUKE DETECTADO",
        description=f"**{count}** {event_type} foram detectados em curto período!",
        color=EmbedColors.ERROR,
        timestamp=datetime.utcnow()
    )
    
    if actor:
        embed.add_field(name="👤 Suspeito", value=f"{actor.mention} (`{actor.id}`)", inline=True)
    
    embed.add_field(
        name="🛡️ Ação",
        value="Permissões foram revogadas e o incidente foi registrado.",
        inline=False
    )
    
    return embed


def appeal_embed(
    user: discord.Member,
    infraction_id: int,
    appeal_reason: str
) -> discord.Embed:
    """Cria um embed para apelações."""
    embed = discord.Embed(
        title="📨 Nova Apelação",
        color=EmbedColors.WARNING,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="👤 Usuário", value=f"{user.mention} (`{user.id}`)", inline=True)
    embed.add_field(name="🆔 ID da Infração", value=str(infraction_id), inline=True)
    embed.add_field(name="📝 Motivo da Apelação", value=appeal_reason, inline=False)
    
    return embed


def config_embed(config: dict, guild_name: str) -> discord.Embed:
    """Cria um embed mostrando a configuração atual."""
    embed = discord.Embed(
        title=f"⚙️ Configuração de {guild_name}",
        color=EmbedColors.INFO,
        timestamp=datetime.utcnow()
    )
    
    # Auto-moderação
    automod = config.get('automod', {})
    embed.add_field(
        name="🤖 Auto-Moderação",
        value=f"Status: {'✅ Ativo' if automod.get('enabled') else '❌ Inativo'}",
        inline=True
    )
    
    # Anti-raid
    antiraid = config.get('anti_raid', {})
    embed.add_field(
        name="🛡️ Anti-Raid",
        value=f"Status: {'✅ Ativo' if antiraid.get('enabled') else '❌ Inativo'}",
        inline=True
    )
    
    # Anti-nuke
    antinuke = config.get('anti_nuke', {})
    embed.add_field(
        name="⚠️ Anti-Nuke",
        value=f"Status: {'✅ Ativo' if antinuke.get('enabled') else '❌ Inativo'}",
        inline=True
    )
    
    # Logging
    logging = config.get('logging', {})
    log_channel = logging.get('log_channel_id')
    embed.add_field(
        name="📝 Logs",
        value=f"Canal: {f'<#{log_channel}>' if log_channel else 'Não configurado'}",
        inline=True
    )
    
    # Permissões
    perms = config.get('permissions', {})
    mod_role = perms.get('mod_role_id')
    embed.add_field(
        name="👮 Cargo de Moderador",
        value=f"{f'<@&{mod_role}>' if mod_role else 'Não configurado'}",
        inline=True
    )
    
    return embed
