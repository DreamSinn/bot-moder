# 🚀 Guia de Início Rápido

Este guia vai te ajudar a colocar o bot funcionando em menos de 10 minutos!

## ⚡ Instalação Rápida

### 1. Pré-requisitos

- Python 3.11+ instalado
- Conta Discord com permissões de administrador no servidor

### 2. Criar o Bot no Discord

1. Acesse: https://discord.com/developers/applications
2. Clique em **"New Application"**
3. Dê um nome (ex: "Mod Bot")
4. Vá em **"Bot"** → **"Add Bot"**
5. **Copie o Token** (guarde com segurança!)
6. Ative os **Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent

### 3. Instalar o Bot

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd discord-mod-bot

# Instale as dependências
pip install -r requirements.txt

# Configure o token
cp .env.example .env
nano .env  # Cole seu token aqui
```

No arquivo `.env`, adicione:
```env
DISCORD_TOKEN=seu_token_aqui
```

### 4. Convidar o Bot

1. No Developer Portal, vá em **"OAuth2"** → **"URL Generator"**
2. Selecione:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Permissões:
   - ✅ Administrator (ou permissões específicas)
4. Copie o link e abra no navegador
5. Selecione seu servidor e autorize

### 5. Iniciar o Bot

```bash
python src/bot.py
```

Você deve ver:
```
Bot conectado como SeuBot (ID: ...)
Conectado a 1 servidores
```

## ⚙️ Configuração Inicial

No Discord, execute estes comandos:

### 1. Configurar Canal de Logs
```
/config logs #logs
```

### 2. Ativar Auto-Moderação
```
/config automod enabled:True
```

### 3. Configurar Anti-Raid
```
/config antiraid enabled:True threshold:10 time_window:60
```

### 4. Testar o Bot
```
/help
```

## 🎯 Comandos Essenciais

### Moderação Básica
```
/ban @usuario motivo:"Spam"
/kick @usuario motivo:"Comportamento inadequado"
/mute @usuario duration:1h motivo:"Flood"
/warn @usuario motivo:"Linguagem imprópria"
```

### Gerenciamento de Canal
```
/purge amount:50
/lock channel:#geral
/slowmode channel:#geral seconds:10
```

### Verificar Infrações
```
/infractions @usuario
```

## 🐳 Usando Docker (Alternativa)

Se preferir usar Docker:

```bash
# Com SQLite
docker-compose up -d bot

# Com PostgreSQL (produção)
docker-compose up -d
```

## 🔧 Solução de Problemas

### Bot não responde
- ✅ Verifique se os **Intents** estão habilitados
- ✅ Confirme que o **token** está correto
- ✅ Verifique os **logs** para erros

### Comandos não aparecem
- ⏰ Aguarde até 1 hora para sincronização
- 🔄 Reinicie o bot
- ✅ Confirme permissão `applications.commands`

### Erro de permissão
- 📊 Bot deve estar **acima** dos cargos que modera
- ✅ Verifique permissões no servidor

## 📚 Próximos Passos

1. Leia o [README.md](README.md) completo
2. Configure palavras bloqueadas: `/config badwords`
3. Defina cargo de moderador: `/config modrole`
4. Explore todos os comandos: `/help`

## 💡 Dicas

- **Backup**: Faça backup regular do arquivo `modbot.db`
- **Logs**: Monitore o canal de logs configurado
- **Testes**: Teste comandos em servidor de desenvolvimento primeiro
- **Segurança**: Nunca compartilhe seu token do bot

## 🆘 Precisa de Ajuda?

- 📖 Documentação completa: [README.md](README.md)
- 🐛 Reportar bugs: Use o sistema de Issues
- 💬 Perguntas: Use a aba Discussions

---

**Pronto! Seu bot está funcionando! 🎉**
