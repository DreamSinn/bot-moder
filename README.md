# 🛡️ Bot de Moderação para Discord

Bot completo e profissional de moderação para Discord, desenvolvido em Python com discord.py 2.3+. Oferece funcionalidades avançadas de moderação, auto-moderação inteligente, proteções anti-raid e anti-nuke, sistema robusto de logs e muito mais.

## ✨ Funcionalidades

### 🔨 Comandos de Moderação

- **`/ban`** - Bane um usuário permanentemente do servidor
- **`/tempban`** - Bane um usuário temporariamente (com expiração automática)
- **`/unban`** - Remove o banimento de um usuário
- **`/kick`** - Expulsa um usuário do servidor
- **`/mute`** - Silencia um usuário por tempo determinado
- **`/unmute`** - Remove o silenciamento de um usuário
- **`/warn`** - Aplica uma advertência a um usuário
- **`/infractions`** - Lista todas as infrações de um usuário
- **`/purge`** - Deleta múltiplas mensagens de um canal

### 🤖 Auto-Moderação

- **Detecção de Spam** - Identifica e pune automaticamente mensagens repetitivas
- **Filtro de Links** - Whitelist/blacklist de URLs permitidas
- **Bloqueio de Convites** - Impede convites para outros servidores Discord
- **Filtro de Palavras** - Lista customizável de palavras proibidas
- **Verificação de Anexos** - Bloqueia arquivos suspeitos e grandes

### 🛡️ Proteções Avançadas

- **Anti-Raid** - Detecta e previne ataques de raid (join floods)
- **Anti-Nuke** - Monitora e previne deleção/criação em massa de canais e cargos
- **Sistema de Escalonamento** - Aumenta automaticamente a severidade das punições

### 📝 Sistema de Logs e Auditoria

- **Logs Completos** - Registra todas as ações de moderação
- **Audit Trail** - Histórico detalhado de eventos do servidor
- **Exportação de Logs** - Exporta histórico em formato texto
- **Logs de Mensagens** - Registra edições e deleções (opcional)

### ⚙️ Configuração Flexível

- **`/config view`** - Visualiza a configuração atual
- **`/config logs`** - Define o canal de logs
- **`/config modrole`** - Define o cargo de moderador
- **`/config automod`** - Ativa/desativa auto-moderação
- **`/config antiraid`** - Configura proteção anti-raid
- **`/config antinuke`** - Configura proteção anti-nuke
- **`/config badwords`** - Gerencia lista de palavras bloqueadas

### 🛠️ Utilitários

- **`/slowmode`** - Define modo lento em canais
- **`/lock`** - Bloqueia um canal
- **`/unlock`** - Desbloqueia um canal
- **`/appeal`** - Sistema de apelação de infrações
- **`/help`** - Mostra ajuda sobre os comandos

## 🚀 Instalação

### Pré-requisitos

- Python 3.11 ou superior
- pip (gerenciador de pacotes Python)
- Conta de desenvolvedor Discord

### Passo 1: Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd discord-mod-bot
```

### Passo 2: Instalar Dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure:

```env
DISCORD_TOKEN=seu_token_aqui
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///modbot.db
LOG_LEVEL=INFO
SUPER_ADMIN_IDS=seu_id_discord
```

### Passo 4: Criar o Bot no Discord

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em "New Application"
3. Dê um nome ao seu bot
4. Vá para a seção "Bot" e clique em "Add Bot"
5. Copie o token e cole no arquivo `.env`
6. Ative os seguintes **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
   - ✅ Presence Intent (opcional)

### Passo 5: Convidar o Bot

1. Vá para a seção "OAuth2" > "URL Generator"
2. Selecione os scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Selecione as permissões:
   - ✅ Administrator (ou permissões específicas abaixo)

**Permissões Necessárias:**
- Manage Roles
- Manage Channels
- Kick Members
- Ban Members
- Moderate Members
- Manage Messages
- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Use Slash Commands

4. Copie o link gerado e abra no navegador
5. Selecione o servidor e autorize

### Passo 6: Executar o Bot

```bash
python src/bot.py
```

## 🐳 Docker

### Usando Docker Compose

```bash
docker-compose up -d
```

### Build Manual

```bash
docker build -t discord-mod-bot .
docker run -d --env-file .env discord-mod-bot
```

## 📊 Banco de Dados

### SQLite (Padrão)

O bot usa SQLite por padrão, sem necessidade de configuração adicional.

```env
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///modbot.db
```

### PostgreSQL (Produção)

Para ambientes de produção, recomenda-se PostgreSQL:

```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@host:port/database
```

## ⚙️ Configuração Inicial

Após adicionar o bot ao servidor:

1. **Configure o canal de logs:**
   ```
   /config logs #canal-de-logs
   ```

2. **Defina o cargo de moderador (opcional):**
   ```
   /config modrole @Moderador
   ```

3. **Ative a auto-moderação:**
   ```
   /config automod enabled:True
   ```

4. **Configure proteção anti-raid:**
   ```
   /config antiraid enabled:True threshold:10 time_window:60
   ```

5. **Adicione palavras bloqueadas (opcional):**
   ```
   /config badwords words:palavra1,palavra2,palavra3
   ```

## 🧪 Testes

Execute os testes unitários:

```bash
pytest
```

Com cobertura:

```bash
pytest --cov=src --cov-report=html
```

Execute apenas testes específicos:

```bash
pytest tests/test_utils.py -v
```

## 🔧 Desenvolvimento

### Estrutura do Projeto

```
discord-mod-bot/
├── src/
│   ├── bot.py              # Arquivo principal do bot
│   ├── cogs/               # Módulos de comandos
│   │   ├── moderation.py   # Comandos de moderação
│   │   ├── automod.py      # Auto-moderação
│   │   ├── audit.py        # Sistema de logs
│   │   └── config.py       # Configuração
│   └── utils/              # Utilitários
│       ├── database.py     # Gerenciamento de BD
│       ├── embeds.py       # Embeds padronizados
│       ├── errors.py       # Tratamento de erros
│       ├── permissions.py  # Sistema de permissões
│       └── scheduler.py    # Tarefas agendadas
├── tests/                  # Testes automatizados
├── config.json             # Configuração padrão
├── requirements.txt        # Dependências Python
├── Dockerfile             # Container Docker
└── README.md              # Documentação

```

### Adicionando Novos Comandos

1. Crie ou edite um arquivo em `src/cogs/`
2. Implemente o comando usando `@app_commands.command`
3. Registre o cog em `src/bot.py`

Exemplo:

```python
@app_commands.command(name="exemplo", description="Comando de exemplo")
async def exemplo(self, interaction: discord.Interaction):
    await interaction.response.send_message("Olá!")
```

### Linting e Formatação

```bash
# Formatação com black
black src/

# Linting com flake8
flake8 src/

# Type checking com mypy
mypy src/
```

## 🔐 Segurança

- ✅ Verificação de hierarquia de cargos
- ✅ Validação de permissões antes de cada ação
- ✅ Sanitização de entradas para prevenir injeção
- ✅ Rate limiting automático
- ✅ Logs estruturados e sanitizados
- ✅ Proteção contra self-actions
- ✅ Lista de super-admins com bypass configurável

## 📈 Monitoramento

### Logs

Os logs são salvos em formato JSON estruturado para fácil parsing:

```bash
tail -f logs/bot.log
```

### Métricas

O bot registra métricas básicas:
- Total de ações de moderação
- Eventos de auto-moderação
- Erros e exceções

### Health Check (Opcional)

Configure um endpoint de health check:

```env
ENABLE_HEALTH_CHECK=true
HEALTH_CHECK_PORT=8080
```

## 🌍 Internacionalização

O bot está em português por padrão. Para adicionar outros idiomas:

1. Crie um arquivo de tradução em `src/locales/`
2. Implemente o sistema de i18n
3. Configure o idioma padrão em `config.json`

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🆘 Suporte

### Problemas Comuns

**Bot não responde aos comandos:**
- Verifique se os intents estão habilitados no Developer Portal
- Confirme que o bot tem permissões adequadas
- Verifique os logs para erros

**Comandos não aparecem:**
- Aguarde até 1 hora para sincronização global
- Use comandos de guild para sincronização instantânea
- Verifique se o bot tem permissão `applications.commands`

**Erro de permissão:**
- Verifique a hierarquia de cargos (bot deve estar acima dos cargos que modera)
- Confirme que o bot tem as permissões necessárias no servidor

### Contato

- **Issues:** Use o sistema de issues do GitHub
- **Discussões:** Use a aba Discussions para perguntas

## 🎯 Roadmap

- [ ] Dashboard web para configuração
- [ ] Sistema de tickets
- [ ] Comandos de música
- [ ] Sistema de níveis e XP
- [ ] Integração com APIs externas
- [ ] Suporte a múltiplos idiomas
- [ ] Sistema de backup automático
- [ ] Analytics e estatísticas avançadas

## 📚 Recursos Adicionais

- [Documentação do discord.py](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

**Desenvolvido com ❤️ para a comunidade Discord**
#   b o t - m o d e r  
 