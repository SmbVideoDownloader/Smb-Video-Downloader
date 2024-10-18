import os
import tempfile
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from yt_dlp import YoutubeDL
from typing import Tuple

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file for OAuth2
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# Set up basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

def download_media(url: str, format_type: str) -> Tuple[str, str]:
    """Download media with non-Opus audio and return the temp file path and filename."""
    ydl_opts = {
        'format': 'bestvideo+bestaudio',  # Get the best video and audio streams
        'noplaylist': True,               # Don't download playlists
        'cookiefile': COOKIES_FILE,       # Use cookies if necessary for authentication
        'quiet': False,                   # Keep detailed output for debugging
        'outtmpl': '/tmp/%(id)s.%(ext)s', # Set output template for temp files
        'merge_output_format': 'mp4',     # Merge output into MP4 format
        'overwrites': True,               # Overwrite existing files
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',   # Convert video to mp4
                'preferedformat': 'mp4',
            },
            {
                'key': 'FFmpegAudioFix',         # Ensure audio is converted to a supported format
                'preferredcodec': 'aac',         # Convert audio to AAC (not Opus)
                'preferredquality': '192',       # Set quality for AAC
            },
            {
                'key': 'FFmpegEmbedSubtitle',    # Optionally embed subtitles if available
            },
        ]
    }

    try:
        # Fetch metadata to get the video ID (optional but useful)
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id", "")
            filename = f"{video_id}.mp4"

        # Set a temporary file name for storing the download
        temp_file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        ydl_opts['outtmpl'] = temp_file_path  # Update the output template

        # Perform the actual download and processing
        with YoutubeDL(ydl_opts) as ydl_inner:
            ydl_inner.download([url])

        # Check if the file exists and is not empty
        if os.path.getsize(temp_file_path) == 0:
            logging.error(f"Downloaded file is empty: {temp_file_path}")
            os.remove(temp_file_path)
            raise Exception("Downloaded file is empty.")

        return temp_file_path, filename

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        raise e

# Route to initiate download
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')  # Assume 'video' if not specified

    if not url:
        logging.warning("No URL provided in the request.")
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the media as a temp file
        temp_file_path, filename = download_media(url, format_type=format_type)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(temp_file_path)
                logging.info(f"Deleted temp file: {temp_file_path}")
            except Exception as e:
                logging.error(f"Error deleting temp file {temp_file_path}: {str(e)}")
            return response

        # Use Flask's send_file to return the file, prompting a download on the client side
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4' if format_type == 'video' else 'audio/mpeg'  # Set the correct MIME type
        )

    except Exception as e:
        logging.error(f"Error in download route: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route to get video info
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

# Cleanup thread to delete old files
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
cleanup_thread = threading.Thread(target=cleanup_downloads, args=('/tmp',), daemon=True)  # Adjust this as needed
cleanup_thread.start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000, channel_timeout=300)  # Run with Waitress, 5 min timeout
