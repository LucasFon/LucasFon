@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        # Simular um cliente web real para evitar o bloqueio anti-bot do YouTube
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    if os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Vídeo sem título'),
                'thumbnail': info.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_file():
    data = request.get_json()
    url = data.get('url')
    tipo = data.get('type', 'video')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        # O mesmo ajuste de cliente para o download não ser barrado
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    if tipo == 'audio':
        ydl_opts['format'] = 'ba'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'bv*+ba/b'

    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    if os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if tipo == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'
            
            basename = os.path.basename(filename)
            return jsonify({
                'download_link': f"/download-file/{basename}",
                'filename': basename
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
