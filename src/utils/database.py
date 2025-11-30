"""
Sistema de banco de dados com suporte a SQLite e PostgreSQL.
Gerencia todas as operações de persistência do bot.
"""

import os
import json
import aiosqlite
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class Database:
    """Classe principal para gerenciamento do banco de dados."""
    
    def __init__(self, db_type: str = "sqlite", db_url: str = "modbot.db"):
        self.db_type = db_type
        self.db_url = db_url
        self.conn = None
        
    async def connect(self):
        """Estabelece conexão com o banco de dados."""
        try:
            if self.db_type == "sqlite":
                self.conn = await aiosqlite.connect(self.db_url)
                self.conn.row_factory = aiosqlite.Row
                await logger.ainfo("Conectado ao SQLite", database=self.db_url)
            elif self.db_type == "postgresql":
                import asyncpg
                self.conn = await asyncpg.connect(self.db_url)
                await logger.ainfo("Conectado ao PostgreSQL")
            else:
                raise ValueError(f"Tipo de banco de dados não suportado: {self.db_type}")
            
            await self.create_tables()
        except Exception as e:
            await logger.aerror("Erro ao conectar ao banco de dados", error=str(e))
            raise
    
    async def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            await self.conn.close()
            await logger.ainfo("Conexão com banco de dados fechada")
    
    async def create_tables(self):
        """Cria todas as tabelas necessárias."""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS infractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS mutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            muted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS mod_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            target_id INTEGER,
            action_type TEXT NOT NULL,
            reason TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS configs (
            guild_id INTEGER PRIMARY KEY,
            config_data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS automod_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            content TEXT,
            action_taken TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_infractions_user ON infractions(user_id, guild_id);
        CREATE INDEX IF NOT EXISTS idx_infractions_active ON infractions(active, expires_at);
        CREATE INDEX IF NOT EXISTS idx_mutes_active ON mutes(active, expires_at);
        CREATE INDEX IF NOT EXISTS idx_mod_actions_guild ON mod_actions(guild_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_guild ON audit_logs(guild_id);
        """
        
        if self.db_type == "sqlite":
            await self.conn.executescript(schema)
            await self.conn.commit()
        else:
            # Para PostgreSQL, executar cada statement separadamente
            statements = [s.strip() for s in schema.split(';') if s.strip()]
            for statement in statements:
                await self.conn.execute(statement)
        
        await logger.ainfo("Tabelas criadas/verificadas com sucesso")
    
    async def add_user(self, user_id: int, username: str, joined_at: datetime = None):
        """Adiciona ou atualiza um usuário."""
        try:
            if self.db_type == "sqlite":
                await self.conn.execute(
                    """INSERT OR REPLACE INTO users (user_id, username, joined_at)
                       VALUES (?, ?, ?)""",
                    (user_id, username, joined_at or datetime.utcnow())
                )
                await self.conn.commit()
            else:
                await self.conn.execute(
                    """INSERT INTO users (user_id, username, joined_at)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (user_id) DO UPDATE SET username = $2, joined_at = $3""",
                    user_id, username, joined_at or datetime.utcnow()
                )
        except Exception as e:
            await logger.aerror("Erro ao adicionar usuário", user_id=user_id, error=str(e))
            raise
    
    async def add_infraction(
        self,
        user_id: int,
        guild_id: int,
        moderator_id: int,
        infraction_type: str,
        reason: str = None,
        expires_at: datetime = None
    ) -> int:
        """Adiciona uma infração."""
        try:
            if self.db_type == "sqlite":
                cursor = await self.conn.execute(
                    """INSERT INTO infractions (user_id, guild_id, moderator_id, type, reason, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, guild_id, moderator_id, infraction_type, reason, expires_at)
                )
                await self.conn.commit()
                return cursor.lastrowid
            else:
                row = await self.conn.fetchrow(
                    """INSERT INTO infractions (user_id, guild_id, moderator_id, type, reason, expires_at)
                       VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                    user_id, guild_id, moderator_id, infraction_type, reason, expires_at
                )
                return row['id']
        except Exception as e:
            await logger.aerror("Erro ao adicionar infração", user_id=user_id, error=str(e))
            raise
    
    async def get_infractions(self, user_id: int, guild_id: int, active_only: bool = False) -> List[Dict]:
        """Retorna infrações de um usuário."""
        try:
            query = """SELECT * FROM infractions WHERE user_id = ? AND guild_id = ?"""
            params = [user_id, guild_id]
            
            if active_only:
                query += " AND active = 1"
            
            query += " ORDER BY created_at DESC"
            
            if self.db_type == "sqlite":
                async with self.conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                rows = await self.conn.fetch(query.replace('?', '$'), *params)
                return [dict(row) for row in rows]
        except Exception as e:
            await logger.aerror("Erro ao buscar infrações", user_id=user_id, error=str(e))
            return []
    
    async def count_infractions(self, user_id: int, guild_id: int, days: int = 30) -> int:
        """Conta infrações recentes de um usuário."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            if self.db_type == "sqlite":
                async with self.conn.execute(
                    """SELECT COUNT(*) as count FROM infractions 
                       WHERE user_id = ? AND guild_id = ? AND created_at > ? AND active = 1""",
                    (user_id, guild_id, cutoff)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row['count'] if row else 0
            else:
                row = await self.conn.fetchrow(
                    """SELECT COUNT(*) as count FROM infractions 
                       WHERE user_id = $1 AND guild_id = $2 AND created_at > $3 AND active = 1""",
                    user_id, guild_id, cutoff
                )
                return row['count'] if row else 0
        except Exception as e:
            await logger.aerror("Erro ao contar infrações", user_id=user_id, error=str(e))
            return 0
    
    async def add_mute(
        self,
        user_id: int,
        guild_id: int,
        moderator_id: int,
        reason: str = None,
        expires_at: datetime = None
    ) -> int:
        """Adiciona um mute."""
        try:
            if self.db_type == "sqlite":
                cursor = await self.conn.execute(
                    """INSERT INTO mutes (user_id, guild_id, moderator_id, reason, expires_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, guild_id, moderator_id, reason, expires_at)
                )
                await self.conn.commit()
                return cursor.lastrowid
            else:
                row = await self.conn.fetchrow(
                    """INSERT INTO mutes (user_id, guild_id, moderator_id, reason, expires_at)
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    user_id, guild_id, moderator_id, reason, expires_at
                )
                return row['id']
        except Exception as e:
            await logger.aerror("Erro ao adicionar mute", user_id=user_id, error=str(e))
            raise
    
    async def remove_mute(self, user_id: int, guild_id: int):
        """Remove um mute ativo."""
        try:
            if self.db_type == "sqlite":
                await self.conn.execute(
                    """UPDATE mutes SET active = 0 
                       WHERE user_id = ? AND guild_id = ? AND active = 1""",
                    (user_id, guild_id)
                )
                await self.conn.commit()
            else:
                await self.conn.execute(
                    """UPDATE mutes SET active = 0 
                       WHERE user_id = $1 AND guild_id = $2 AND active = 1""",
                    user_id, guild_id
                )
        except Exception as e:
            await logger.aerror("Erro ao remover mute", user_id=user_id, error=str(e))
            raise
    
    async def get_expired_mutes(self) -> List[Dict]:
        """Retorna mutes expirados que ainda estão ativos."""
        try:
            now = datetime.utcnow()
            
            if self.db_type == "sqlite":
                async with self.conn.execute(
                    """SELECT * FROM mutes 
                       WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= ?""",
                    (now,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                rows = await self.conn.fetch(
                    """SELECT * FROM mutes 
                       WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= $1""",
                    now
                )
                return [dict(row) for row in rows]
        except Exception as e:
            await logger.aerror("Erro ao buscar mutes expirados", error=str(e))
            return []
    
    async def get_expired_bans(self) -> List[Dict]:
        """Retorna tempbans expirados."""
        try:
            now = datetime.utcnow()
            
            if self.db_type == "sqlite":
                async with self.conn.execute(
                    """SELECT * FROM infractions 
                       WHERE type = 'tempban' AND active = 1 
                       AND expires_at IS NOT NULL AND expires_at <= ?""",
                    (now,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                rows = await self.conn.fetch(
                    """SELECT * FROM infractions 
                       WHERE type = 'tempban' AND active = 1 
                       AND expires_at IS NOT NULL AND expires_at <= $1""",
                    now
                )
                return [dict(row) for row in rows]
        except Exception as e:
            await logger.aerror("Erro ao buscar bans expirados", error=str(e))
            return []
    
    async def log_action(
        self,
        guild_id: int,
        moderator_id: int,
        action_type: str,
        target_id: int = None,
        reason: str = None,
        metadata: Dict = None
    ):
        """Registra uma ação de moderação."""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            if self.db_type == "sqlite":
                await self.conn.execute(
                    """INSERT INTO mod_actions (guild_id, moderator_id, target_id, action_type, reason, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (guild_id, moderator_id, target_id, action_type, reason, metadata_json)
                )
                await self.conn.commit()
            else:
                await self.conn.execute(
                    """INSERT INTO mod_actions (guild_id, moderator_id, target_id, action_type, reason, metadata)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    guild_id, moderator_id, target_id, action_type, reason, metadata_json
                )
        except Exception as e:
            await logger.aerror("Erro ao registrar ação", action_type=action_type, error=str(e))
    
    async def get_guild_config(self, guild_id: int) -> Optional[Dict]:
        """Retorna a configuração de uma guild."""
        try:
            if self.db_type == "sqlite":
                async with self.conn.execute(
                    "SELECT config_data FROM configs WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return json.loads(row['config_data']) if row else None
            else:
                row = await self.conn.fetchrow(
                    "SELECT config_data FROM configs WHERE guild_id = $1",
                    guild_id
                )
                return json.loads(row['config_data']) if row else None
        except Exception as e:
            await logger.aerror("Erro ao buscar config", guild_id=guild_id, error=str(e))
            return None
    
    async def save_guild_config(self, guild_id: int, config: Dict):
        """Salva a configuração de uma guild."""
        try:
            config_json = json.dumps(config)
            
            if self.db_type == "sqlite":
                await self.conn.execute(
                    """INSERT OR REPLACE INTO configs (guild_id, config_data, updated_at)
                       VALUES (?, ?, ?)""",
                    (guild_id, config_json, datetime.utcnow())
                )
                await self.conn.commit()
            else:
                await self.conn.execute(
                    """INSERT INTO configs (guild_id, config_data, updated_at)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (guild_id) DO UPDATE SET config_data = $2, updated_at = $3""",
                    guild_id, config_json, datetime.utcnow()
                )
        except Exception as e:
            await logger.aerror("Erro ao salvar config", guild_id=guild_id, error=str(e))
            raise
    
    async def log_automod_event(
        self,
        guild_id: int,
        user_id: int,
        event_type: str,
        content: str = None,
        action_taken: str = None
    ):
        """Registra um evento de auto-moderação."""
        try:
            if self.db_type == "sqlite":
                await self.conn.execute(
                    """INSERT INTO automod_events (guild_id, user_id, event_type, content, action_taken)
                       VALUES (?, ?, ?, ?, ?)""",
                    (guild_id, user_id, event_type, content, action_taken)
                )
                await self.conn.commit()
            else:
                await self.conn.execute(
                    """INSERT INTO automod_events (guild_id, user_id, event_type, content, action_taken)
                       VALUES ($1, $2, $3, $4, $5)""",
                    guild_id, user_id, event_type, content, action_taken
                )
        except Exception as e:
            await logger.aerror("Erro ao registrar evento automod", error=str(e))
