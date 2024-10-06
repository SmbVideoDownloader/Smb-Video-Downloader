import subprocess
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import tempfile
import shutil
import logging

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Directory to save downloads
DOWNLOAD_DIR = "/var/www/v2mp4.com/downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

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

    try:
        # Construct yt-dlp command with cookies
        command = [
            'yt-dlp', 
            '--cookies', 
            '/var/www/v2mp4.com/cookies/cookies.txt', 
            url
        ]

        # Run the command
        result = subprocess.run(command, capture_output=True, text=True)

        # Check if the command was successful
        if result.returncode != 0:
            return jsonify({'error': f'Failed to download: {result.stderr}'}), 500
        
        # Extract the filename from the result
        file_name = result.stdout.strip()  # Get the last line of stdout for the filename

        return jsonify({'file': file_name}), 200

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
def download_file():
    # Get the filename from the query parameters
    filename = request.args.get('file')

    if not filename:
        return jsonify({'error': 'No file name provided'}), 400

    try:
        # Construct the full file path
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)  # Change port if needed
