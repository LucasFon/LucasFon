FROM python:3.10-slim

# Instalar o FFmpeg (essencial para juntar áudio e vídeo)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Forçar a atualização do yt-dlp para a versão mais recente a cada build
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY . .

EXPOSE 10000

# Iniciar a aplicação em produção utilizando o Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
