from flask import Flask, request, send_file, render_template_string, jsonify
import yt_dlp
import os
import subprocess
import re

app = Flask(__name__)

# Dosya isimlerini temizleme
def temiz_dosya_adi(isim):
    return re.sub(r'[\\/*?:"<>|]', "", isim)

HTML_SAYFASI = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Pro Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0b0e11; }
        .tt-gradient { background: linear-gradient(90deg, #ff0050 0%, #00f2ea 100%); }
    </style>
</head>
<body class="text-white min-h-screen flex items-center justify-center p-4 font-sans">
    <div class="bg-gray-900 p-8 rounded-3xl shadow-2xl w-full max-w-xl border border-gray-800">
        <h1 class="text-4xl font-black text-center mb-8 tracking-tighter italic">Tik<span class="text-[#ff0050]">Tok</span> PRO</h1>
        
        <div id="inputArea" class="space-y-4">
            <input type="text" id="videoUrl" placeholder="TikTok video linkini yapıştır..." 
                class="w-full bg-gray-800 border-2 border-gray-700 p-4 rounded-xl focus:outline-none focus:border-[#00f2ea] text-white">
            <button onclick="bilgiGetir()" id="getBtn" class="w-full tt-gradient py-4 rounded-xl font-bold uppercase tracking-widest hover:opacity-90 transition">Video Bilgisi Getir</button>
        </div>

        <div id="infoArea" class="hidden mt-8 border-t border-gray-800 pt-6">
            <div class="flex flex-col md:flex-row gap-6 mb-6 items-center">
                <img id="thumb" src="" class="w-32 h-32 rounded-xl shadow-lg object-cover border-2 border-gray-700">
                <div class="flex-1 text-center md:text-left">
                    <h3 id="title" class="font-bold text-lg leading-tight mb-2"></h3>
                    <p class="text-gray-400 text-sm">İndirmek istediğiniz kaliteyi seçin:</p>
                </div>
            </div>
            
            <div id="qualityOptions" class="grid grid-cols-1 gap-3"></div>
            <button onclick="window.location.reload()" class="w-full mt-6 text-gray-500 text-xs hover:underline uppercase tracking-tighter">Farklı Link Dene</button>
        </div>

        <div id="status" class="hidden mt-6 text-center">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-[#00f2ea] mb-2"></div>
            <p id="statusText" class="text-xs text-gray-400 font-mono"></p>
        </div>
    </div>

    <script>
        async function bilgiGetir() {
            const url = document.getElementById('videoUrl').value;
            if(!url) return alert("Lütfen link gir!");
            
            document.getElementById('getBtn').disabled = true;
            document.getElementById('status').classList.remove('hidden');
            document.getElementById('statusText').innerText = "VİDEO İNCELENİYOR...";

            try {
                const response = await fetch('/bilgi', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `url=${encodeURIComponent(url)}`
                });
                const data = await response.json();
                
                if(data.error) throw data.error;

                document.getElementById('thumb').src = data.thumbnail;
                document.getElementById('title').innerText = data.title;
                
                const qDiv = document.getElementById('qualityOptions');
                qDiv.innerHTML = '';
                
                [{l:'360p (Hızlı)', v:'360'}, {l:'720p (HD)', v:'720'}, {l:'1080p (Full HD)', v:'1080'}].forEach(q => {
                    const btn = document.createElement('button');
                    btn.className = "bg-gray-800 hover:bg-gray-700 border border-gray-700 p-4 rounded-xl w-full flex justify-between font-bold transition-all";
                    btn.innerHTML = `<span>${q.l}</span> <span class="text-[#ff0050]">MP4</span>`;
                    btn.onclick = () => indir(url, q.v);
                    qDiv.appendChild(btn);
                });

                document.getElementById('inputArea').classList.add('hidden');
                document.getElementById('infoArea').classList.remove('hidden');
            } catch (e) {
                alert("Hata: Linki kontrol edin veya az sonra tekrar deneyin.");
                console.error(e);
            } finally {
                document.getElementById('status').classList.add('hidden');
                document.getElementById('getBtn').disabled = false;
            }
        }

        function indir(url, kalite) {
            document.getElementById('infoArea').classList.add('opacity-30', 'pointer-events-none');
            document.getElementById('status').classList.remove('hidden');
            document.getElementById('statusText').innerText = kalite + "P HAZIRLANIYOR...";
            
            const form = document.createElement('form');
            form.method = 'POST'; form.action = '/indir';
            const u = document.createElement('input'); u.name = 'url'; u.value = url;
            const q = document.createElement('input'); q.name = 'kalite'; q.value = kalite;
            form.appendChild(u); form.appendChild(q);
            document.body.appendChild(form);
            form.submit();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def ana_sayfa():
    return render_template_string(HTML_SAYFASI)

@app.route('/bilgi', methods=['POST'])
def bilgi_ver():
    url = request.form.get('url').strip()
    # TikTok engelini aşmak için tarayıcı gibi davranıyoruz
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'TikTok Video'),
                'thumbnail': info.get('thumbnail', ''),
                'success': True
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/indir', methods=['POST'])
def indir():
    url = request.form.get('url')
    kalite = request.form.get('kalite')
    
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        video_basligi = temiz_dosya_adi(info.get('title', 'video'))

    # Render'da geçici dosya yazmak için /tmp/ klasörü en güvenlisidir
    gecici = f"/tmp/temp_{video_basligi}.mp4"
    final = f"/tmp/{video_basligi}_{kalite}p.mp4"

    ydl_opts = {
        'outtmpl': gecici,
        'format': f'bestvideo[height<={kalite}][ext=mp4]+bestaudio[ext=m4a]/best[height<={kalite}][ext=mp4]/best',
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Hızlı çevirme işlemi (HEVC -> H264)
    subprocess.run([
        "ffmpeg", "-y", "-i", gecici,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-pix_fmt", "yuv420p", final
    ])
    
    if os.path.exists(gecici): os.remove(gecici)
    return send_file(final, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)