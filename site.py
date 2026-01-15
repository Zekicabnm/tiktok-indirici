from flask import Flask, request, send_file, render_template_string, jsonify
import yt_dlp
import os
import subprocess
import re

app = Flask(__name__)

def temiz_dosya_adi(isim):
    return re.sub(r'[\\/*?:"<>|]', "", isim)

HTML_SAYFASI = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #010101; }
        .tt-gradient { background: linear-gradient(90deg, #ff0050 0%, #00f2ea 100%); }
    </style>
</head>
<body class="text-white min-h-screen flex items-center justify-center p-4">
    <div class="bg-gray-900 p-8 rounded-3xl shadow-2xl w-full max-w-lg border border-gray-800">
        <h1 class="text-4xl font-black text-center mb-8 italic">Tik<span class="text-[#ff0050]">Tok</span></h1>
        
        <div id="inputArea" class="space-y-4">
            <input type="text" id="videoUrl" placeholder="TikTok video linkini yapıştır..." 
                class="w-full bg-gray-800 border-2 border-gray-700 p-4 rounded-xl focus:outline-none focus:border-[#00f2ea] text-white">
            <button onclick="bilgiGetir()" id="getBtn" class="w-full tt-gradient py-4 rounded-xl font-bold uppercase tracking-widest">Video Bilgisini Getir</button>
        </div>

        <div id="infoArea" class="hidden mt-8 border-t border-gray-800 pt-6 text-center">
            <img id="thumb" src="" class="w-48 h-auto mx-auto rounded-lg mb-4 shadow-lg">
            <h3 id="title" class="font-bold text-lg mb-2"></h3>
            <p id="size" class="text-[#00f2ea] font-mono mb-6"></p>
            
            <form action="/indir" method="post" onsubmit="indiriliyor()">
                <input type="hidden" name="url" id="finalUrl">
                <button type="submit" class="w-full bg-white text-black py-4 rounded-xl font-black uppercase hover:bg-gray-200 transition">VİDEOYU ŞİMDİ İNDİR</button>
            </form>
        </div>

        <div id="status" class="hidden mt-4 text-center text-sm text-gray-500 italic">İşlem yapılıyor...</div>
    </div>

    <script>
        async function bilgiGetir() {
            const url = document.getElementById('videoUrl').value;
            if(!url) return alert("Link gir!");
            
            document.getElementById('getBtn').disabled = true;
            document.getElementById('status').classList.remove('hidden');
            document.getElementById('status').innerText = "Video bilgileri çekiliyor...";

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
                document.getElementById('size').innerText = "Tahmini Boyut: " + data.filesize + " MB";
                document.getElementById('finalUrl').value = url;
                
                document.getElementById('inputArea').classList.add('hidden');
                document.getElementById('infoArea').classList.remove('hidden');
            } catch (e) {
                alert("Hata: " + e);
            } finally {
                document.getElementById('status').classList.add('hidden');
                document.getElementById('getBtn').disabled = false;
            }
        }

        function indiriliyor() {
            document.getElementById('status').classList.remove('hidden');
            document.getElementById('status').innerText = "Video dönüştürülüyor ve indirme başlıyor...";
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
    url = request.form.get('url')
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            # Boyutu MB cinsinden hesapla
            size_bytes = info.get('filesize') or info.get('filesize_approx') or 0
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            return jsonify({
                'title': info.get('title', 'TikTok Videosu'),
                'thumbnail': info.get('thumbnail'),
                'filesize': size_mb if size_mb > 0 else "Bilinmiyor"
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/indir', methods=['POST'])
def indir():
    url = request.form.get('url')
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        video_basligi = temiz_dosya_adi(info.get('title', 'tiktok_video'))

    gecici = f"temp_{video_basligi}.mp4"
    final = f"{video_basligi}.mp4"

    # Hızlı indirme ayarı
    with yt_dlp.YoutubeDL({'outtmpl': gecici, 'format': 'best[ext=mp4]/best'}) as ydl:
        ydl.download([url])

    # Hızlı çevirme (HEVC -> H264)
    subprocess.run(["ffmpeg", "-y", "-i", gecici, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-pix_fmt", "yuv420p", final])
    
    if os.path.exists(gecici): os.remove(gecici)
    return send_file(final, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)