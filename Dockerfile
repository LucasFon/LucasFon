FROM python:3.11-slim

# Instalar o FFmpeg (essencial para juntar áudio e vídeo)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY . .

EXPOSE 10000

# Iniciar o Gunicorn com um timeout de 120 segundos para evitar o erro de Worker Timeout
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "220"]
