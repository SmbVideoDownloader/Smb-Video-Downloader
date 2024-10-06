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
            '--cookies-from-browser',
            'firefox',
            url
        ]

        # Run the command
        result = subprocess.run(command, capture_output=True, text=True, shell=True)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Check if the command was successful
        if result.returncode != 0:
            return jsonify({'error': f'Failed to download: {result.stderr.strip()}'}), 500

        # Extract the filename from the output (modify based on your needs)
        output_lines = result.stdout.strip().split('\n')
        file_name = output_lines[-1] if output_lines else "Downloaded file"  # Adjust as necessary

        return jsonify({'file': file_name}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Helper function to download video using yt-dlp with OAuth2
def run_yt_dlp_command(url):
    try:
        # Command for yt-dlp with OAuth2 login
        command = [
            'env/bin/yt-dlp',  # Adjust to the correct path of yt-dlp
            '--username', 'oauth2',
            '--password', '',
            '--cookies', 
            '/var/www/v2mp4.com/cookies/cookies.txt',  # Path to cookies file
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

# API route to get video information and download using yt-dlp
@app.route("/get_video_info", methods=["POST"])
def get_video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Use yt-dlp to download video using OAuth2
        success, result = run_yt_dlp_command(url)

        if not success:
            return jsonify({'error': f'Failed to download: {result}'}), 500

        # Extract video info using yt-dlp without downloading
        ydl_opts = {'noplaylist': True, 'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        return jsonify({
            'title': info_dict.get('title', 'No title'),
            'thumbnail': info_dict.get('thumbnail', ''),
            'success': True
        })

    except Exception as e:
        app.logger.error(f"Error occurred: {str(e)}")  # Log the error for debugging
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
    #serve(app, host="0.0.0.0", port=8000)  # Change port if needed
    app.run(host="0.0.0.0", port=8000, debug=True)
