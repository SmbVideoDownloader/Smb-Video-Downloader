import subprocess
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os
import tempfile
import shutil
import logging
import re

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Directory to save downloads
DOWNLOAD_DIR = "/var/www/v2mp4.com/downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg" # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('index.html') # This will serve index.html from the templates directory

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> str:
    temp_dir = tempfile.mkdtemp()
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(id)s-%(ext)s'),  # Use video ID instead of full title
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH # Ensure FFmpeg is located by yt-dlp
    }

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_name = ydl.prepare_filename(info_dict)
        output_path = os.path.join(DOWNLOAD_DIR, f"{info_dict['id']}.mp4")

        # Merge video and audio if needed
        if format_type == 'video':
            ffmpeg_command = f'"{FFMPEG_PATH}" -i "{file_name}" -c copy "{output_path}"'
            os.system(ffmpeg_command)
        else:
            shutil.copy(file_name, output_path)

        # Clean up temp directory
        shutil.rmtree(temp_dir)
        return output_path

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Construct yt-dlp command with cookies and output as mp4
        command = [
            'yt-dlp',
            '--trim-filenames', '200',  # Limit filename length to 200 characters
            '--cookies', '/var/www/v2mp4.com/cookies/cookies.txt',
            '--username', 'oauth2',
            '--password', '',
            '-o', '%(title)s.%(ext)s', # Forces output to be in MP4 format
            '-f', 'bestvideo+bestaudio/best', # Best quality
            '-v', # Enable verbose output
            url
        ]

        # Run the command
        result = subprocess.run(command, capture_output=True, text=True)

        # Check if the command was successful
        if result.returncode != 0:
            # Check for specific 504 error
            if isinstance(result.stderr, str) and 'Gateway Time-out' in result.stderr:
                return jsonify({'error': 'Server timeout occurred during download'}), 504
            else:
                return jsonify({'error': f'Failed to download: {result.stderr.strip()}'}), 500

        # Send the downloaded file directly
        file_path = f"{result.stdout.strip()}.mp4"
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500




# Helper function to run yt-dlp with cookies
def run_yt_dlp_command(url):
    try:
        # Command for yt-dlp with OAuth2 and cookies
        command = [
            'yt-dlp', # Assuming yt-dlp is in the system's PATH
            '--cookies', '/var/www/v2mp4.com/cookies/cookies.txt', # Replace with the correct cookies path
            '--username', 'oauth2', # OAuth2-based authentication
            '--password', '', # Blank since we're using OAuth2
            url
        ]

        # Running the command and capturing output
        result = subprocess.run(command, capture_output=True, text=True)

        # Log the command output for debugging purposes
        if result.returncode != 0:
            error_message = result.stderr.strip() if result.stderr else "Unknown error occurred."
            app.logger.error(f"yt-dlp failed: {error_message}")
            return False, error_message

        return True, result.stdout

    except Exception as e:
        app.logger.error(f"Error running yt-dlp command: {str(e)}")
        return False, str(e)

# API route for getting video info
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
            'cookiefile': '/var/www/v2mp4.com/cookies/cookies.txt' # Path to cookies file
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
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Send the downloaded file directly
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    from waitress import serve
    #serve(app, host="0.0.0.0", port=8000)  # Change port if needed
    app.run(host="0.0.0.0", port=8000, debug=True)