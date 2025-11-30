"""
Testes unitários para módulos utilitários.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.scheduler import parse_duration, format_duration


class TestSchedulerUtils:
    """Testes para funções de duração."""
    
    def test_parse_duration_seconds(self):
        """Testa parse de segundos."""
        assert parse_duration("10s") == timedelta(seconds=10)
        assert parse_duration("30sec") == timedelta(seconds=30)
        assert parse_duration("45seconds") == timedelta(seconds=45)
    
    def test_parse_duration_minutes(self):
        """Testa parse de minutos."""
        assert parse_duration("5m") == timedelta(minutes=5)
        assert parse_duration("15min") == timedelta(minutes=15)
        assert parse_duration("30minutes") == timedelta(minutes=30)
    
    def test_parse_duration_hours(self):
        """Testa parse de horas."""
        assert parse_duration("1h") == timedelta(hours=1)
        assert parse_duration("2hour") == timedelta(hours=2)
        assert parse_duration("12hours") == timedelta(hours=12)
    
    def test_parse_duration_days(self):
        """Testa parse de dias."""
        assert parse_duration("1d") == timedelta(days=1)
        assert parse_duration("7day") == timedelta(days=7)
        assert parse_duration("30days") == timedelta(days=30)
    
    def test_parse_duration_weeks(self):
        """Testa parse de semanas."""
        assert parse_duration("1w") == timedelta(weeks=1)
        assert parse_duration("2week") == timedelta(weeks=2)
        assert parse_duration("4weeks") == timedelta(weeks=4)
    
    def test_parse_duration_invalid(self):
        """Testa parse de durações inválidas."""
        assert parse_duration("invalid") is None
        assert parse_duration("10x") is None
        assert parse_duration("abc123") is None
        assert parse_duration("") is None
    
    def test_format_duration_seconds(self):
        """Testa formatação de segundos."""
        td = timedelta(seconds=30)
        assert "30 segundo" in format_duration(td)
    
    def test_format_duration_minutes(self):
        """Testa formatação de minutos."""
        td = timedelta(minutes=15)
        assert "15 minuto" in format_duration(td)
    
    def test_format_duration_hours(self):
        """Testa formatação de horas."""
        td = timedelta(hours=2)
        assert "2 hora" in format_duration(td)
    
    def test_format_duration_days(self):
        """Testa formatação de dias."""
        td = timedelta(days=3)
        assert "3 dia" in format_duration(td)
    
    def test_format_duration_complex(self):
        """Testa formatação de durações complexas."""
        td = timedelta(days=2, hours=3, minutes=15)
        result = format_duration(td)
        assert "2 dia" in result
        assert "3 hora" in result
        assert "15 minuto" in result


@pytest.mark.asyncio
class TestPermissions:
    """Testes para sistema de permissões."""
    
    async def test_hierarchy_owner_bypass(self):
        """Testa que o owner pode agir em qualquer um."""
        from utils.permissions import check_hierarchy
        
        # Mock guild, moderator, target, bot
        guild = Mock()
        guild.owner_id = 123
        
        moderator = Mock()
        moderator.id = 123  # É o owner
        
        target = Mock()
        target.id = 456
        target.top_role = Mock()
        
        bot_member = Mock()
        bot_member.top_role = Mock()
        
        # Owner deve poder agir
        result = await check_hierarchy(guild, moderator, target, bot_member)
        assert result is True
    
    async def test_hierarchy_self_action(self):
        """Testa que não pode agir em si mesmo."""
        from utils.permissions import check_hierarchy, HierarchyError
        
        guild = Mock()
        guild.owner_id = 999
        
        moderator = Mock()
        moderator.id = 123
        
        target = Mock()
        target.id = 123  # Mesmo ID
        
        bot_member = Mock()
        
        # Deve lançar erro
        with pytest.raises(HierarchyError):
            await check_hierarchy(guild, moderator, target, bot_member)
    
    async def test_hierarchy_owner_target(self):
        """Testa que não pode agir no owner."""
        from utils.permissions import check_hierarchy, HierarchyError
        
        guild = Mock()
        guild.owner_id = 456
        
        moderator = Mock()
        moderator.id = 123
        
        target = Mock()
        target.id = 456  # É o owner
        
        bot_member = Mock()
        
        # Deve lançar erro
        with pytest.raises(HierarchyError):
            await check_hierarchy(guild, moderator, target, bot_member)


@pytest.mark.asyncio
class TestDatabase:
    """Testes para operações de banco de dados."""
    
    @pytest.fixture
    async def db(self):
        """Fixture para criar banco de dados de teste."""
        from utils.database import Database
        
        # Usar banco em memória
        db = Database("sqlite", ":memory:")
        await db.connect()
        yield db
        await db.close()
    
    async def test_add_user(self, db):
        """Testa adição de usuário."""
        await db.add_user(123, "TestUser", datetime.utcnow())
        
        # Verificar se foi adicionado
        async with db.conn.execute("SELECT * FROM users WHERE user_id = ?", (123,)) as cursor:
            user = await cursor.fetchone()
            assert user is not None
            assert user['username'] == "TestUser"
    
    async def test_add_infraction(self, db):
        """Testa adição de infração."""
        # Adicionar usuário primeiro
        await db.add_user(123, "TestUser")
        
        # Adicionar infração
        infraction_id = await db.add_infraction(
            123,
            999,
            456,
            'warn',
            'Test reason'
        )
        
        assert infraction_id > 0
        
        # Verificar se foi adicionado
        infractions = await db.get_infractions(123, 999)
        assert len(infractions) == 1
        assert infractions[0]['type'] == 'warn'
        assert infractions[0]['reason'] == 'Test reason'
    
    async def test_count_infractions(self, db):
        """Testa contagem de infrações."""
        await db.add_user(123, "TestUser")
        
        # Adicionar múltiplas infrações
        await db.add_infraction(123, 999, 456, 'warn', 'Reason 1')
        await db.add_infraction(123, 999, 456, 'warn', 'Reason 2')
        await db.add_infraction(123, 999, 456, 'mute', 'Reason 3')
        
        # Contar
        count = await db.count_infractions(123, 999, days=30)
        assert count == 3
    
    async def test_add_and_remove_mute(self, db):
        """Testa adição e remoção de mute."""
        await db.add_user(123, "TestUser")
        
        # Adicionar mute
        expires_at = datetime.utcnow() + timedelta(hours=1)
        mute_id = await db.add_mute(123, 999, 456, "Test mute", expires_at)
        
        assert mute_id > 0
        
        # Remover mute
        await db.remove_mute(123, 999)
        
        # Verificar se foi removido
        async with db.conn.execute(
            "SELECT * FROM mutes WHERE user_id = ? AND guild_id = ? AND active = 1",
            (123, 999)
        ) as cursor:
            mute = await cursor.fetchone()
            assert mute is None
    
    async def test_guild_config(self, db):
        """Testa salvamento e recuperação de configuração."""
        config = {
            'automod': {'enabled': True},
            'anti_raid': {'enabled': True}
        }
        
        # Salvar
        await db.save_guild_config(999, config)
        
        # Recuperar
        retrieved = await db.get_guild_config(999)
        
        assert retrieved is not None
        assert retrieved['automod']['enabled'] is True
        assert retrieved['anti_raid']['enabled'] is True


@pytest.mark.asyncio
class TestEmbeds:
    """Testes para criação de embeds."""
    
    def test_success_embed(self):
        """Testa criação de embed de sucesso."""
        from utils.embeds import success_embed, EmbedColors
        
        embed = success_embed("Test Title", "Test Description")
        
        assert embed.title == "Test Title"
        assert embed.description == "Test Description"
        assert embed.color == EmbedColors.SUCCESS
    
    def test_error_embed(self):
        """Testa criação de embed de erro."""
        from utils.embeds import error_embed, EmbedColors
        
        embed = error_embed("Error Title", "Error Description")
        
        assert embed.title == "Error Title"
        assert embed.description == "Error Description"
        assert embed.color == EmbedColors.ERROR
    
    def test_moderation_action_embed(self):
        """Testa criação de embed de ação de moderação."""
        from utils.embeds import moderation_action_embed
        
        target = Mock()
        target.mention = "<@123>"
        target.id = 123
        
        moderator = Mock()
        moderator.mention = "<@456>"
        
        embed = moderation_action_embed(
            "BAN",
            target,
            moderator,
            "Test reason",
            "1 day",
            999
        )
        
        assert "BAN" in embed.title
        assert len(embed.fields) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
