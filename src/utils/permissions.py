"""
Sistema de verificação de permissões e hierarquia.
Garante que ações de moderação respeitem a hierarquia de cargos.
"""

import discord
from discord.ext import commands
from typing import Optional, List
import structlog

from .errors import PermissionError, HierarchyError

logger = structlog.get_logger()


async def check_hierarchy(
    guild: discord.Guild,
    moderator: discord.Member,
    target: discord.Member,
    bot_member: discord.Member
) -> bool:
    """
    Verifica se a hierarquia permite a ação.
    
    Args:
        guild: A guild onde a ação ocorre
        moderator: O moderador executando a ação
        target: O alvo da ação
        bot_member: O membro do bot
    
    Returns:
        True se a hierarquia permite
    
    Raises:
        HierarchyError: Se a hierarquia não permitir
    """
    
    # Owner sempre pode
    if moderator.id == guild.owner_id:
        return True
    
    # Não pode agir em si mesmo
    if moderator.id == target.id:
        raise HierarchyError("Você não pode executar ações de moderação em si mesmo.")
    
    # Não pode agir no owner
    if target.id == guild.owner_id:
        raise HierarchyError("Não é possível executar ações de moderação no dono do servidor.")
    
    # Verificar hierarquia do moderador
    if moderator.top_role <= target.top_role:
        raise HierarchyError(
            f"Você não pode executar esta ação em {target.mention} pois ele tem um cargo igual ou superior ao seu."
        )
    
    # Verificar hierarquia do bot
    if bot_member.top_role <= target.top_role:
        raise HierarchyError(
            f"Não posso executar esta ação em {target.mention} pois ele tem um cargo igual ou superior ao meu."
        )
    
    return True


async def check_bot_permissions(
    guild: discord.Guild,
    channel: discord.TextChannel,
    *permissions: str
) -> bool:
    """
    Verifica se o bot tem as permissões necessárias.
    
    Args:
        guild: A guild
        channel: O canal
        *permissions: Lista de permissões necessárias
    
    Returns:
        True se tem todas as permissões
    
    Raises:
        PermissionError: Se faltar alguma permissão
    """
    bot_member = guild.me
    bot_permissions = channel.permissions_for(bot_member)
    
    missing = []
    for perm in permissions:
        if not getattr(bot_permissions, perm, False):
            missing.append(perm)
    
    if missing:
        raise PermissionError(
            f"Estou sem as seguintes permissões necessárias: {', '.join(missing)}"
        )
    
    return True


async def check_moderator_permissions(
    member: discord.Member,
    *permissions: str
) -> bool:
    """
    Verifica se o moderador tem as permissões necessárias.
    
    Args:
        member: O membro
        *permissions: Lista de permissões necessárias
    
    Returns:
        True se tem todas as permissões
    
    Raises:
        PermissionError: Se faltar alguma permissão
    """
    missing = []
    for perm in permissions:
        if not getattr(member.guild_permissions, perm, False):
            missing.append(perm)
    
    if missing:
        raise PermissionError(
            f"Você não tem as seguintes permissões necessárias: {', '.join(missing)}"
        )
    
    return True


def is_moderator(member: discord.Member, mod_role_id: Optional[int] = None) -> bool:
    """
    Verifica se um membro é moderador.
    
    Args:
        member: O membro a verificar
        mod_role_id: ID do cargo de moderador (opcional)
    
    Returns:
        True se é moderador
    """
    # Owner sempre é moderador
    if member.id == member.guild.owner_id:
        return True
    
    # Verificar permissões de moderação
    if member.guild_permissions.administrator:
        return True
    
    if member.guild_permissions.ban_members or member.guild_permissions.kick_members:
        return True
    
    # Verificar cargo específico de moderador
    if mod_role_id:
        return any(role.id == mod_role_id for role in member.roles)
    
    return False


def is_admin(member: discord.Member, admin_role_id: Optional[int] = None) -> bool:
    """
    Verifica se um membro é administrador.
    
    Args:
        member: O membro a verificar
        admin_role_id: ID do cargo de admin (opcional)
    
    Returns:
        True se é administrador
    """
    # Owner sempre é admin
    if member.id == member.guild.owner_id:
        return True
    
    # Verificar permissão de administrador
    if member.guild_permissions.administrator:
        return True
    
    # Verificar cargo específico de admin
    if admin_role_id:
        return any(role.id == admin_role_id for role in member.roles)
    
    return False


def is_super_admin(user_id: int, super_admin_ids: List[int]) -> bool:
    """
    Verifica se um usuário é super admin (bypass total).
    
    Args:
        user_id: ID do usuário
        super_admin_ids: Lista de IDs de super admins
    
    Returns:
        True se é super admin
    """
    return user_id in super_admin_ids


async def can_execute_action(
    action: str,
    moderator: discord.Member,
    target: discord.Member,
    config: dict,
    super_admin_ids: List[int] = None
) -> bool:
    """
    Verifica se um moderador pode executar uma ação específica.
    
    Args:
        action: Nome da ação (ban, kick, mute, etc)
        moderator: O moderador
        target: O alvo
        config: Configuração da guild
        super_admin_ids: Lista de super admins
    
    Returns:
        True se pode executar
    
    Raises:
        PermissionError ou HierarchyError se não puder
    """
    guild = moderator.guild
    bot_member = guild.me
    
    # Super admins podem tudo
    if super_admin_ids and is_super_admin(moderator.id, super_admin_ids):
        return True
    
    # Verificar hierarquia
    check_hierarchy_enabled = config.get('permissions', {}).get('check_hierarchy', True)
    if check_hierarchy_enabled:
        await check_hierarchy(guild, moderator, target, bot_member)
    
    # Verificar permissões específicas por ação
    action_permissions = {
        'ban': ('ban_members',),
        'unban': ('ban_members',),
        'kick': ('kick_members',),
        'mute': ('moderate_members',),
        'unmute': ('moderate_members',),
        'warn': ('kick_members',),
        'timeout': ('moderate_members',),
        'role': ('manage_roles',),
        'purge': ('manage_messages',),
        'slowmode': ('manage_channels',),
        'lock': ('manage_channels',),
        'unlock': ('manage_channels',)
    }
    
    required_perms = action_permissions.get(action.lower(), ())
    
    if required_perms:
        await check_moderator_permissions(moderator, *required_perms)
        await check_bot_permissions(guild, target.guild.channels[0], *required_perms)
    
    return True


def has_higher_role(member1: discord.Member, member2: discord.Member) -> bool:
    """
    Verifica se member1 tem cargo superior a member2.
    
    Args:
        member1: Primeiro membro
        member2: Segundo membro
    
    Returns:
        True se member1 tem cargo superior
    """
    return member1.top_role > member2.top_role


async def get_mute_role(guild: discord.Guild) -> Optional[discord.Role]:
    """
    Obtém ou cria o cargo de mute.
    
    Args:
        guild: A guild
    
    Returns:
        O cargo de mute ou None se falhar
    """
    # Procurar cargo existente
    mute_role = discord.utils.get(guild.roles, name="Muted")
    
    if mute_role:
        return mute_role
    
    # Criar novo cargo
    try:
        mute_role = await guild.create_role(
            name="Muted",
            color=discord.Color.dark_gray(),
            reason="Cargo de mute criado automaticamente pelo bot"
        )
        
        # Configurar permissões em todos os canais
        for channel in guild.channels:
            try:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        send_messages_in_threads=False
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(
                        mute_role,
                        speak=False,
                        stream=False
                    )
            except discord.Forbidden:
                await logger.awarning(
                    "Sem permissão para configurar cargo de mute no canal",
                    channel=channel.name
                )
            except Exception as e:
                await logger.aerror(
                    "Erro ao configurar cargo de mute no canal",
                    channel=channel.name,
                    error=str(e)
                )
        
        await logger.ainfo("Cargo de mute criado com sucesso", guild=guild.name)
        return mute_role
        
    except discord.Forbidden:
        await logger.aerror("Sem permissão para criar cargo de mute")
        raise PermissionError("Não tenho permissão para criar o cargo de mute.")
    except Exception as e:
        await logger.aerror("Erro ao criar cargo de mute", error=str(e))
        raise


async def setup_mute_role_permissions(
    channel: discord.abc.GuildChannel,
    mute_role: discord.Role
):
    """
    Configura permissões do cargo de mute em um canal específico.
    
    Args:
        channel: O canal
        mute_role: O cargo de mute
    """
    try:
        if isinstance(channel, discord.TextChannel):
            await channel.set_permissions(
                mute_role,
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False
            )
        elif isinstance(channel, discord.VoiceChannel):
            await channel.set_permissions(
                mute_role,
                speak=False,
                stream=False
            )
        
        await logger.adebug("Permissões de mute configuradas", channel=channel.name)
    except Exception as e:
        await logger.aerror(
            "Erro ao configurar permissões de mute",
            channel=channel.name,
            error=str(e)
        )
