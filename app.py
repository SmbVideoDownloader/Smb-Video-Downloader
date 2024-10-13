import os
import shutil
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file for OAuth2
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

# Helper function to download media with yt-dlp
def download_media(url: str, format_type: str):
    temp_dir = tempfile.mkdtemp()  # Create temp directory for downloading
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'ffmpeg_location': FFMPEG_PATH,
        'cookiefile': COOKIES_FILE,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }],
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            if not info_dict:
                raise ValueError("Failed to retrieve video information.")
            
            file_name = ydl.prepare_filename(info_dict)
            if format_type == 'video':
                final_file = f"{os.path.splitext(file_name)[0]}.mp4"
            else:
                final_file = file_name

            if not final_file or not os.path.exists(final_file):
                raise ValueError("Final file not found or download failed.")

            return final_file, temp_dir

    except Exception as e:
        shutil.rmtree(temp_dir)
        raise e

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_type = request.form.get('format_type', 'video')

    temp_dir = None  # Initialize temp_dir

    try:
        # Download media and get the file path
        file_path, temp_dir = download_media(url, format_type)

        # Stream the file to the user for download
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

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

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)  # Run with Waitress
