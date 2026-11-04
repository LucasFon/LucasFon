import os
import requests
from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baixar Vídeo e Áudio do YouTube</title>
    <!-- Tailwind CSS para estilização -->
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">

    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-2xl text-center">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">Baixar Vídeo e Áudio do YouTube</h1>
        <p class="text-gray-600 mb-6">Cole o link do YouTube abaixo para converter e baixar em MP3 ou MP4 com áudio perfeito.</p>

        <!-- Formulário para Inserir a URL -->
        <div class="flex flex-col sm:flex-row gap-3 mb-6">
            <input 
                type="text" 
                id="urlInput" 
                placeholder="Cole o link do YouTube aqui..." 
                class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-700"
            />
            <button 
                onclick="buscarInformacoes()" 
                id="btnBuscar"
                class="bg-red-600 hover:bg-red-700 text-white font-semibold px-6 py-3 rounded-lg transition duration-200"
            >
                Começar
            </button>
        </div>

        <!-- Mensagens de Estado -->
        <div id="statusMessage" class="hidden my-4 text-center text-gray-700 font-medium"></div>

        <!-- Resultados (Título, Thumbnail e Botões) -->
        <div id="resultContainer" class="hidden border-t pt-6 text-left">
            <div class="flex flex-col md:flex-row gap-4 items-center mb-6">
                <img id="videoThumb" class="w-full md:w-48 rounded-lg shadow" src="" alt="Thumbnail do Vídeo">
                <div>
                    <h2 id="videoTitle" class="font-bold text-lg text-gray-800"></h2>
                </div>
            </div>

            <!-- Botões de Download -->
            <div class="flex flex-col gap-3">
                <button 
                    onclick="fazerDownload('video')" 
                    id="btnDownloadVideo"
                    class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg flex justify-between items-center transition duration-200"
                >
                    <span>Baixar Vídeo (MP4 com Áudio)</span>
                    <span class="bg-green-800 text-xs px-2 py-1 rounded">HD</span>
                </button>

                <button 
                    onclick="fazerDownload('audio')" 
                    id="btnDownloadAudio"
                    class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg flex justify-between items-center transition duration-200"
                >
                    <span>Baixar Áudio (MP3)</span>
                    <span class="bg-blue-800 text-xs px-2 py-1 rounded">192 kbps</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Script de Integração -->
    <script>
        const API_BASE = window.location.origin;
        let currentUrl = "";

        async function buscarInformacoes() {
            let rawUrl = document.getElementById("urlInput").value.trim();
            const statusMessage = document.getElementById("statusMessage");
            const resultContainer = document.getElementById("resultContainer");

            if (!rawUrl) {
                alert("Por favor, insira um link do YouTube válido.");
                return;
            }

            currentUrl = rawUrl;

            resultContainer.classList.add("hidden");
            statusMessage.classList.remove("hidden", "text-red-600");
            statusMessage.classList.add("text-gray-700");
            statusMessage.innerHTML = "Obtendo informações do vídeo...";

            try {
                const response = await fetch(`${API_BASE}/api/info`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: rawUrl })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Erro ao buscar detalhes do vídeo.");
                }

                document.getElementById("videoTitle").innerText = data.title;
                document.getElementById("videoThumb").src = data.thumbnail;

                statusMessage.classList.add("hidden");
                resultContainer.classList.remove("hidden");

            } catch (err) {
                statusMessage.classList.remove("text-gray-700");
                statusMessage.classList.add("text-red-600");
                statusMessage.innerText = "Erro no processamento: " + err.message;
            }
        }

        async function fazerDownload(tipo) {
            const statusMessage = document.getElementById("statusMessage");
            const btnVideo = document.getElementById("btnDownloadVideo");
            const btnAudio = document.getElementById("btnDownloadAudio");

            statusMessage.classList.remove("hidden", "text-red-600");
            statusMessage.classList.add("text-gray-700");
            statusMessage.innerText = `A descarregar e a converter ${tipo === 'audio' ? 'para MP3' : 'vídeo com áudio (MP4)'}... Aguarde.`;

            btnVideo.disabled = true;
            btnAudio.disabled = true;

            try {
                const response = await fetch(`${API_BASE}/api/download`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        url: currentUrl, 
                        type: tipo 
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Erro ao descarregar o ficheiro.");
                }

                const downloadLinkComCacheBuster = data.download_link + "?t=" + new Date().getTime();

                const link = document.createElement("a");
                link.href = downloadLinkComCacheBuster;
                link.setAttribute("download", data.filename);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                statusMessage.innerText = "Download concluído com sucesso!";

            } catch (err) {
                statusMessage.classList.remove("text-gray-700");
                statusMessage.classList.add("text-red-600");
                statusMessage.innerText = "Erro ao baixar: " + err.message;
            } finally {
                btnVideo.disabled = false;
                btnAudio.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

def extract_video_id(url):
    """Extrai o ID do vídeo de forma segura"""
    if 'v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    return url

def get_invidious_instances():
    """Obtém instâncias ativas do Invidious"""
    instances = []
    try:
        res = requests.get("https://api.invidious.io/instances.json?sort_by=type,health", timeout=4)
        if res.status_code == 200:
            for item in res.json():
                domain = item[0]
                details = item[1]
                if details.get('type') == 'https' and details.get('cors'):
                    instances.append(f"https://{domain}")
    except Exception:
        pass

    if not instances:
        instances = [
            "https://invidious.privacyredirect.com",
            "https://yt.artemislena.eu",
            "https://invidious.perennialte.ch",
            "https://inv.nadeko.net"
        ]
    return instances

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    video_id = extract_video_id(url)
    instances = get_invidious_instances()

    info = None
    for instance in instances[:5]:
        try:
            response = requests.get(f"{instance}/api/v1/videos/{video_id}", timeout=4)
            if response.status_code == 200:
                info = response.json()
                break
        except Exception:
            continue

    if not info:
        return jsonify({'error': 'Não foi possível contactar nenhuma instância do Invidious.'}), 502

    thumbnails = info.get('videoThumbnails', [])
    thumb_url = thumbnails[0].get('url', '') if thumbnails else ''

    return jsonify({
        'title': info.get('title', 'Vídeo sem título'),
        'thumbnail': thumb_url
    })

@app.route('/api/download', methods=['POST'])
def download_file():
    data = request.get_json()
    url = data.get('url')
    tipo = data.get('type', 'video')
    
    if not url:
        return jsonify({'error': 'URL não fornecido'}), 400

    # Configuração inteligente do yt-dlp para garantir que vídeo e áudio vêm unidos corretamente
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
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
        # Garante que descarrega o melhor formato combinado (vídeo + áudio juntos) em MP4
        ydl_opts['format'] = 'best[ext=mp4]/best'

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

@app.route('/download-file/<filename>')
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Ficheiro não encontrado'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
