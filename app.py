import os
from urllib.parse import quote, urlparse, urlunparse
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_clean_proxy():
    proxy_str = os.environ.get("PROXY_URL", "").strip()
    if not proxy_str:
        return None
    
    # Garante o protocolo base
    if not proxy_str.startswith("http://") and not proxy_str.startswith("https://"):
        proxy_str = f"http://{proxy_str}"
        
    try:
        parsed = urlparse(proxy_str)
        # Codifica o utilizador e a senha para evitar conflitos com carateres especiais e múltiplos dois pontos
        if parsed.username or parsed.password:
            user = quote(parsed.username) if parsed.username else ""
            pwd = quote(parsed.password) if parsed.password else ""
            netloc = f"{user}:{pwd}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            parsed = parsed._replace(netloc=netloc)
            return urlunparse(parsed)
    except Exception as e:
        print(f"[AVISO] Erro ao formatar proxy: {e}")
        
    return proxy_str

def get_ydl_opts(extra_opts=None):
    proxy_url = get_clean_proxy()
    
    opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": {
                "player_client": ["mweb", "android"]
            }
        }
    }
    
    if proxy_url:
        opts["proxy"] = proxy_url
        print(f"[DEBUG] Proxy formatado e injetado com sucesso.")
    else:
        print("[AVISO] Nenhum proxy detetado.")

    if extra_opts:
        opts.update(extra_opts)
    return opts

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL nao fornecida"}), 400
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get("formats", []):
                if f.get("ext") in ["mp4", "m4a", "webm", "mp3"]:
                    formats.append({
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "resolution": f.get("format_note") or f"{f.get('height', 'Audio')}p",
                        "filesize": f.get("filesize") or 0
                    })
            return jsonify({
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "formats": formats
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    format_id = data.get("format_id")
    download_type = data.get("type", "video")
    if not url:
        return jsonify({"error": "URL necessaria"}), 400

    if download_type == "audio":
        ydl_opts = get_ydl_opts({
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s"),
            "restrictfilenames": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts = get_ydl_opts({
            "format": format_id if format_id else "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s"),
            "restrictfilenames": True,
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            filename = ydl.prepare_filename(info)
            if download_type == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            basename = os.path.basename(filename)

            file_url = url_for('serve_file', filename=basename, _external=True)
            return jsonify({
                "download_link": file_url,
                "filename": basename
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
