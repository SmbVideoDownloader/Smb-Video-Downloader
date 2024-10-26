import os
import logging
import threading
import time
import requests
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO
import random

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file for OAuth2
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# List of User-Agents to mimic natural traffic
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.99 Mobile Safari/537.36",
    # Add more updated User-Agent strings here
]

# List of proxies (Optional: Add working proxies or use a rotating proxy service)
PROXIES = [
    "https://189.240.60.164:9090",
    "https://15.235.153.57:8089",
    # Add more proxies or integrate with a rotating proxy API
]

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

@app.route("/contact.html")
def contact_us():
    return render_template('contact.html')

@app.route("/terms.html")
def terms():
    return render_template('terms.html')

@app.route("/about.html")
def about():
    return render_template('about.html')

@app.route("/privacy.html")
def privacy():
    return render_template('privacy.html')

@app.route("/index.html")
def index():
    return render_template('index.html')

# Helper function to download video/audio with dynamic headers and proxies
def download_media(url: str, format_type: str) -> str:
    """Download media and return the path to the temp file."""
    
    # Set up yt-dlp options, including User-Agent, proxies, and cookies
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,
        'quiet': False,
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'keepvideo': True,  # Keep original files
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com'
        },
        'proxy': random.choice(PROXIES) if PROXIES else None,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            logging.info(f"Extracted info: {info_dict}")

            # Prepare filename based on video title or ID
            if format_type == 'video':
                ext = 'webm'  # Assuming you want to download video in webm
                temp_file_path = f"/tmp/{info_dict['id']}.mp4.webm"
            else:
                ext = 'mp3'
                temp_file_path = f"/tmp/{info_dict['id']}.mp3"

        # Check if the file already exists
        if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
            logging.info(f"File already exists and is valid: {temp_file_path}")
        else:
            ydl_opts['outtmpl'] = temp_file_path

            # Perform the download
            with YoutubeDL(ydl_opts) as ydl_inner:
                ydl_inner.download([url])

            # Check if the downloaded file is empty
            if os.path.getsize(temp_file_path) == 0:
                logging.error(f"Downloaded file is empty: {temp_file_path}")
                raise Exception("Downloaded file is empty.")

        return temp_file_path

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        raise e

# Route to initiate download
@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')

    if not url:
        logging.warning("No URL provided in the request.")
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the media as a temp file
        temp_file_path = download_media(url, format_type=format_type)
        filename = os.path.basename(temp_file_path)

        # Read the file content to serve it
        with open(temp_file_path, 'rb') as f:
            video_data = f.read()

        # Use Flask's Response to return the BytesIO object
        response = Response(
            video_data,
            mimetype='video/mp4' if format_type == 'video' else 'audio/mpeg',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

        return response

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
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
            'cookiefile': COOKIES_FILE,
            'http_headers': {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.youtube.com'
            },
            'proxy': random.choice(PROXIES) if PROXIES else None,
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

# Cleanup thread to delete old files (Optional, if you want to keep it)
def cleanup_downloads(folder, max_age_seconds=59):
    """Delete files older than max_age_seconds in the specified folder."""
    while True:
        now = time.time()
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        logging.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {str(e)}")
        time.sleep(600)  # Run every 10 minutes

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_downloads, args=('/tmp',), daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000, channel_timeout=300)  # Run with Waitress, 5 min timeout
