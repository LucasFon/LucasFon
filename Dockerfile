FROM python:3.10-slim

# Instalar o FFmpeg (essencial para o yt-dlp juntar áudio e vídeo)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

# Iniciar a aplicação em produção utilizando o Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
