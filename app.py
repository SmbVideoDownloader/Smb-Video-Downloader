import os
import shutil
import tempfile
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
from yt_dlp import YoutubeDL
from typing import Tuple
from io import BytesIO
from flask import Response

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file for OAuth2
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Temporary storage for download files
DOWNLOAD_FOLDER = 'downloads'

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> BytesIO:
    """Download media and return it as an in-memory file-like object."""
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,  # Path to cookies for authentication
        'quiet': True,  # Reduce yt-dlp output
        'outtmpl': '-',  # Output to stdout, using '-' in yt-dlp
    }

    buffer = BytesIO()  # Create an in-memory buffer
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)  # Just get info first

            # Prepare filename based on video title or ID
            filename = f"{info_dict['id']}.mp4" if format_type == 'video' else f"{info_dict['id']}.mp3"

            # Capture download content into buffer
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                # The downloaded content will be put into the buffer.

        buffer.seek(0)  # Move cursor to start of the buffer
        return buffer, filename  # Return buffer with data and filename

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        raise e

# Route to download and stream file
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the media as an in-memory file-like object
        media_file, filename = download_media(url, format_type='video')

        # Use Flask's send_file to return the file, prompting a download on the client side
        return send_file(
            media_file,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'  # Set the correct MIME type for video
        )

    except Exception as e:
        logging.error(f"Error in download route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route("/download-file/<download_id>", methods=["GET"])
def download_file(download_id):
    try:
        file_path = os.path.join(DOWNLOAD_FOLDER, download_id)
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        # Determine the mimetype based on the file extension
        if file_path.endswith('.mp4'):
            mimetype = 'video/mp4'
        elif file_path.endswith('.mp3'):
            mimetype = 'audio/mpeg'
        else:
            mimetype = 'application/octet-stream'

        # Send the file as a downloadable attachment
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype=mimetype
        )
    except Exception as e:
        logging.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Error sending file'}), 500

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

def cleanup_downloads(folder, max_age_seconds=3600):
    """Delete files older than max_age_seconds in the specified folder."""
    while True:
        now = time.time()
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        logging.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {str(e)}")
        time.sleep(600)  # Run every 10 minutes

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_downloads, args=(DOWNLOAD_FOLDER,), daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000, channel_timeout=300)  # Run with Waitress, 5 min timeout
