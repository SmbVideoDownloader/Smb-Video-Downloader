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

# Directory to save downloads on the server
SERVER_DOWNLOAD_DIR = "/var/www/v2mp4.com/Smb-Video-Downloader/downloads"

COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('index.html')  # This will serve index.html from the templates directory

# Helper function to download video/audio and return information
def download_media(url: str, format_type: str) -> dict:
    temp_dir = tempfile.mkdtemp()  # Create temporary directory on user's system
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),  # Use video ID instead of full title
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,  # Ensure FFmpeg is located by yt-dlp
        'trim_filenames': 200  # Limit filename length to 200 characters
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_name = ydl.prepare_filename(info_dict)

        # Merge video and audio if needed (same logic as before)

    # Clean up temp directory on successful download
    if os.path.exists(file_name):
        shutil.rmtree(temp_dir, ignore_errors=True)  # Ignore errors during cleanup

    return {
        'filename': os.path.basename(file_name),  # Return only filename
        'filepath': file_name,  # Return temporary file path
        'title': info_dict.get('title', 'No title'),
        'success': True
    }

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        download_info = download_media(url, 'video')  # Download video and return information
        return jsonify(download_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/get_video_info", methods=["POST"])
def get_video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Use yt-dlp to get video info with cookies
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
            'cookiefile': COOKIES_FILE  # Path to cookies file
        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        return jsonify({
            'title': info_dict.get('title', 'No title'),
            'thumbnail': info_dict.get('thumbnail', ''),
            'success': True
        })

    except Exception as e:
        app.logger.error(f"Error occurred: {str(e)}")
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
        file_path = os.path.join(SERVER_DOWNLOAD_DIR, filename)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Send the downloaded file directly to the user
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    from waitress import serve
    # serve(app, host="0.0.0.0", port=8000)  # Uncomment to run with Waitress
    app.run(host="0.0.0.0", port=8000, debug=True)
