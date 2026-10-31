import os
from urllib.parse import quote
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
    
    # Remove prefixos de protocolo para processamento limpo
    if proxy_str.startswith("http://"):
        proxy_str = proxy_str[7:]
    elif proxy_str.startswith("https://"):
        proxy_str = proxy_str[8:]
        
    # Separação manual segura para evitar o erro de IPv6 do Python
    if "@" in proxy_str:
        auth, host_port = proxy_str.split("@", 1)
        if ":" in auth:
            user, pwd = auth.split(":", 1)
            user_enc = quote(user, safe='')
            pwd_enc = quote(pwd, safe='')
            auth = f"{user_enc}:{pwd_enc}"
        clean_url = f"http://{auth}@{host_port}"
    else:
        clean_url = f"http://{proxy_str}"
        
    print(f"[DEBUG] Proxy processado com sucesso.")
    return clean_url

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
