FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do bot
COPY src/ ./src/
COPY config.json .

# Criar diretório de logs
RUN mkdir -p logs

# Criar usuário não-root
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Comando de inicialização
CMD ["python", "-u", "src/bot.py"]
