import os
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

# Lê o proxy configurado nas variáveis de ambiente do Render
PROXY_URL = os.environ.get('PROXY_URL')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    # Configurações do yt-dlp
    ydl_opts = {
        'format': 'best',
        'cookiefile': 'cookies.txt',
    }

    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_info = {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'formats': [{'format_id': f['format_id'], 'ext': f['ext'], 'resolution': f.get('resolution')} for f in info.get('formats', [])]
            }
            return jsonify(video_info)
    except Exception as e:
        # Devolve o erro exato no JSON para sabermos o que se passa caso volte a falhar
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    output_template = 'downloaded_video.%(ext)s'
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'cookiefile': 'cookies.txt',
    }

    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
