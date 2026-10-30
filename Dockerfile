FROM python:3.10-slim

# Instalar o FFmpeg necessário para conversão de áudio/vídeo
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requisitos.txt .
RUN pip install --no-cache-dir -r requisitos.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
