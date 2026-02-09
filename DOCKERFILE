# Container da API
FROM python:3.12-slim-bookworm

# Define o diretório de trabalho
WORKDIR /app

# Impedir que o Python gere .pyc e garanta logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
