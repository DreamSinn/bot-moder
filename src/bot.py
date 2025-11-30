"""
Bot de Moderação para Discord
Bot completo e profissional com funcionalidades avançadas de moderação.
"""

import discord
from discord.ext import commands
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import structlog
import logging

# Configurar structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configurar logging padrão
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

logger = structlog.get_logger()

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Definir o caminho do banco de dados
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_URL = os.getenv('DATABASE_URL', str(PROJECT_ROOT / 'modbot.db'))

# Se for SQLite e o caminho for relativo (ou URI relativa), torná-lo absoluto
if DATABASE_TYPE == 'sqlite':
    # Remove o prefixo 'sqlite:///' se existir
    db_path = DATABASE_URL.replace('sqlite:///', '', 1)
    
    # Se o caminho for relativo, resolve-o em relação à raiz do projeto
    if not Path(db_path).is_absolute():
        DATABASE_URL = str(PROJECT_ROOT / db_path)
    
    # Se for um URI, reconstrói com o caminho absoluto
    if DATABASE_URL.startswith('sqlite:///'):
        DATABASE_URL = f"sqlite:///{DATABASE_URL.replace('sqlite:///', '', 1)}"
    
    # Se for apenas um caminho de arquivo, usa o caminho absoluto
    else:
        DATABASE_URL = str(Path(DATABASE_URL).resolve())
SUPER_ADMIN_IDS = [int(id.strip()) for id in os.getenv('SUPER_ADMIN_IDS', '').split(',') if id.strip()]
ALERT_CHANNEL_ID = int(os.getenv('ALERT_CHANNEL_ID')) if os.getenv('ALERT_CHANNEL_ID') else None

# Carregar configuração padrão
CONFIG_FILE = Path(__file__).parent.parent / 'config.json'
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    DEFAULT_CONFIG = json.load(f)


class ModBot(commands.Bot):
    """Classe principal do bot de moderação."""
    
    def __init__(self):
        # Configurar intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.moderation = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=commands.when_mentioned,  # Apenas menções, comandos são slash
            intents=intents,
            help_command=None
        )
        
        self.default_config = DEFAULT_CONFIG
        self.super_admin_ids = SUPER_ADMIN_IDS
        self.alert_channel_id = ALERT_CHANNEL_ID
        self.db = None
        self.error_handler = None
        self.scheduler = None
        
        # Cache de configurações por guild
        self.guild_configs = {}
    
    async def setup_hook(self):
        """Inicialização assíncrona do bot."""
        logger.info("Iniciando setup do bot...")
        
        # Importar módulos
        from utils.database import Database
        from utils.errors import ErrorHandler
        from utils.scheduler import TaskScheduler
        
        # Conectar ao banco de dados
        self.db = Database(DATABASE_TYPE, DATABASE_URL)
        await self.db.connect()
        logger.info("Banco de dados conectado")
        
        # Configurar error handler
        self.error_handler = ErrorHandler(self, self.alert_channel_id)
        await self.error_handler.setup()
        logger.info("Error handler configurado")
        
        # Carregar cogs
        await self.load_cogs()
        
        # Iniciar scheduler
        self.scheduler = TaskScheduler(self, self.db)
        logger.info("Scheduler iniciado")
        
        # Sincronizar comandos slash
        logger.info("Sincronizando comandos slash...")
        await self.tree.sync()
        logger.info("Comandos sincronizados")
    
    async def load_cogs(self):
        """Carrega todos os cogs."""
        cogs = [
            'cogs.moderation',
            'cogs.automod',
            'cogs.audit',
            'cogs.config'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog carregado: {cog}")
            except Exception as e:
                logger.error(f"Erro ao carregar cog {cog}: {e}")
    
    async def get_guild_config(self, guild_id: int) -> dict:
        """
        Obtém a configuração de uma guild (com cache).
        
        Args:
            guild_id: ID da guild
        
        Returns:
            Dicionário de configuração
        """
        # Verificar cache
        if guild_id in self.guild_configs:
            return self.guild_configs[guild_id]
        
        # Buscar no banco de dados
        config = await self.db.get_guild_config(guild_id)
        
        # Se não existir, usar padrão
        if not config:
            config = self.default_config.copy()
            await self.db.save_guild_config(guild_id, config)
        
        # Atualizar cache
        self.guild_configs[guild_id] = config
        
        return config
    
    async def update_guild_config(self, guild_id: int, config: dict):
        """
        Atualiza a configuração de uma guild.
        
        Args:
            guild_id: ID da guild
            config: Nova configuração
        """
        await self.db.save_guild_config(guild_id, config)
        self.guild_configs[guild_id] = config
        logger.info(f"Configuração atualizada para guild {guild_id}")
    
    async def on_ready(self):
        """Evento chamado quando o bot está pronto."""
        logger.info(f"Bot conectado como {self.user} (ID: {self.user.id})")
        logger.info(f"Conectado a {len(self.guilds)} servidores")
        
        # Definir status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="𝗔 𝗦𝗘𝗚𝗨𝗥𝗔𝗡𝗖̧𝗔 𝗗𝗢 𝗦𝗘𝗥𝗩𝗜𝗗𝗢𝗥 | /𝗛𝗘𝗟𝗣"
            )
        )
    
    async def on_guild_join(self, guild: discord.Guild):
        """Evento chamado quando o bot entra em um servidor."""
        logger.info(f"Bot adicionado ao servidor: {guild.name} (ID: {guild.id})")
        
        # Criar configuração padrão
        await self.db.save_guild_config(guild.id, self.default_config.copy())
        
        # Tentar enviar mensagem de boas-vindas
        if guild.system_channel:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description=(
                    "Olá! Sou um bot de moderação.\n\n"
                    "**Para começar:**\n"
                    "• Use `/config` para configurar o bot\n"
                    "• Use `/help` para ver todos os comandos\n"
                    "• Configure um canal de logs com `/config logs`\n\n"
                    "**Recursos principais:**\n"
                    "✅ Comandos de moderação completos\n"
                    "✅ Auto-moderação inteligente\n"
                    "✅ Proteção anti-raid e anti-nuke\n"
                    "✅ Sistema de infrações e apelações\n"
                    "✅ Logs detalhados de todas as ações\n\n"
                    "Precisa de ajuda? Use `/help` ou `/config`"
                ),
                color=0x3498db
            )
            
            try:
                await guild.system_channel.send(embed=embed)
            except:
                pass
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Evento chamado quando o bot é removido de um servidor."""
        logger.info(f"Bot removido do servidor: {guild.name} (ID: {guild.id})")
        
        # Remover do cache
        if guild.id in self.guild_configs:
            del self.guild_configs[guild.id]
    
    async def close(self):
        """Fecha o bot e limpa recursos."""
        logger.info("Encerrando bot...")
        
        if self.scheduler:
            self.scheduler.cog_unload()
        
        if self.db:
            await self.db.close()
        
        await super().close()


def main():
    """Função principal para iniciar o bot."""
    if not TOKEN:
        logger.error("Token do Discord não encontrado! Configure a variável DISCORD_TOKEN no arquivo .env")
        sys.exit(1)
    
    # Criar e iniciar o bot
    bot = ModBot()
    
    try:
        bot.run(TOKEN, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Bot encerrado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
