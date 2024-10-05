from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import tempfile
import shutil

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Directory to save downloads
DOWNLOAD_DIR = "/var/www/v2mp4.com/downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

@app.route('/')
def home():
    return render_template('index.html')  # This will serve index.html from the templates directory

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> str:
    temp_dir = tempfile.mkdtemp()
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH  # Ensure FFmpeg is located by yt-dlp
    }
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_name = ydl.prepare_filename(info_dict)
        output_path = os.path.join(DOWNLOAD_DIR, f"{info_dict['title']}.mp4")

        # Merge video and audio if needed
        if format_type == 'video':
            ffmpeg_command = f'"{FFMPEG_PATH}" -i "{file_name}" -c copy "{output_path}"'
            os.system(ffmpeg_command)
        else:
            shutil.copy(file_name, output_path)

        # Clean up temp directory
        shutil.rmtree(temp_dir)
        return output_path

# API route for downloading media
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Use yt-dlp to download the video in the best available format
    try:
        # Setting up the download options to select any available video format
        ydl_opts = {
            'format': 'bestvideo/best',  # This will choose the best video available
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # After download, find the downloaded file
        video_info = ydl.extract_info(url, download=False)
        file_name = f"{video_info['title']}.{ydl.prepare_filename(video_info).split('.')[-1]}"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)

        return jsonify({'file': file_name})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# API route to get video information
@app.route("/get_video_info", methods=["POST"])
def get_video_info():
    data = request.json
    url = data.get('url')

    try:
        with YoutubeDL({'noplaylist': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info_dict.get('title', 'No title'),
                'thumbnail': info_dict.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve downloaded files
@app.route("/download-file", methods=["GET"])
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404



if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)  # Change port if needed
