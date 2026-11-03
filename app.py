import os
import uuid
from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp

app = Flask(__name__)

# Configurações do ambiente
PROXY_URL = os.environ.get('PROXY_URL')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Caminho absoluto para o cookies.txt
COOKIE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')

# Dicionário temporário para mapear IDs únicos aos nomes reais dos arquivos originais
# Isso garante que o navegador receba o nome correto do vídeo na hora de salvar
file_mapping = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baixar Vídeo e Áudio do YouTube</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">

    <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-2xl text-center">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">Baixar Vídeo e Áudio do YouTube</h1>
        <p class="text-gray-600 mb-6">Cole o link do YouTube abaixo para converter e baixar em MP3 ou MP4.</p>

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

        <div id="statusMessage" class="hidden my-4 text-center text-gray-700 font-medium"></div>

        <div id="resultContainer" class="hidden border-t pt-6 text-left">
            <div class="flex flex-col md:flex-row gap-4 items-center mb-6">
                <img id="videoThumb" class="w-full md:w-48 rounded-lg shadow" src="" alt="Thumbnail do Vídeo">
                <div>
                    <h2 id="videoTitle" class="font-bold text-lg text-gray-800"></h2>
                </div>
            </div>

            <div class="flex flex-col gap-3">
                <button 
                    onclick="fazerDownload('video')" 
                    id="btnDownloadVideo"
                    class="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg flex justify-between items-center transition duration-200"
                >
                    <span>Baixar Vídeo (MP4)</span>
                    <span class="bg-green-800 text-xs px-2 py-1 rounded">HD / SD</span>
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
                if (!response.ok) throw new Error(data.error || "Erro ao buscar detalhes.");

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
            statusMessage.innerText = `A descarregar e a converter ${tipo === 'audio' ? 'áudio (MP3)' : 'vídeo (MP4)'}... Aguarde.`;

            btnVideo.disabled = true;
            btnAudio.disabled = true;

            try {
                const response = await fetch(`${API_BASE}/api/download`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: currentUrl, type: tipo })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Erro ao descarregar.");

                statusMessage.innerText = "Download concluído no servidor! Iniciando transferência...";

                // Redireciona o navegador para a rota que entrega e limpa o arquivo
                window.location.href = `${API_BASE}/api/get-file/${data.file_id}`;

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

def obter_opcoes_base():
    """Retorna o dicionário de opções padrão do yt-dlp injetando Cookies e Proxy se existirem"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }
    if PROXY_URL:
        opts['proxy'] = PROXY_URL
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH
    return opts

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400

    ydl_opts = obter_opcoes_base()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Vídeo do YouTube'),
                'thumbnail': info.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({'error': f'Falha ao extrair informações: {str(e)}'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    download_type = data.get('type')  # 'video' ou 'audio'

    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400

    # Gera um identificador único de arquivo para evitar conflito entre múltiplos usuários simultâneos
    file_id = str(uuid.uuid4())
    ydl_opts = obter_opcoes_base()

    if download_type == 'audio':
        caminho_saida = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': caminho_saida,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        extensao_final = "mp3"
    else:
        caminho_saida = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': caminho_saida,
            'merge_output_format': 'mp4',
        })
        extensao_final = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrai os metadados originais primeiro para sabermos o título correto do arquivo
            info = ydl.extract_info(url, download=True)
            titulo_original = info.get('title', 'download').replace('/', '_').replace('\\', '_')
            nome_original_limpo = f"{titulo_original}.{extensao_final}"
            
            nome_arquivo_disco = f"{file_id}.{extensao_final}"

