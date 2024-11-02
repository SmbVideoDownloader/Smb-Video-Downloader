import os
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, Response, abort
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO
from collections import defaultdict
from datetime import datetime, timedelta

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file and OAuth2 token file
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'
OAUTH_FILE = '/var/www/v2mp4.com/oauth2/oauth2_token.json'  # Adjust path as needed

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Rate limiting settings
MAX_REQUESTS = 10  # Maximum requests per IP per minute
TIME_FRAME = 60  # Time frame in seconds (1 minute)
request_counts = defaultdict(list)

@app.before_request
def limit_requests():
    """Rate limit incoming requests based on IP address."""
    ip = request.remote_addr
    current_time = datetime.now()

    # Remove timestamps that are older than the time frame
    request_counts[ip] = [timestamp for timestamp in request_counts[ip] 
                          if timestamp > current_time - timedelta(seconds=TIME_FRAME)]

    # Check if the IP has exceeded the request limit
    if len(request_counts[ip]) >= MAX_REQUESTS:
        logging.warning(f"Rate limit exceeded for IP: {ip}")
        abort(429, description="Too many requests. Please try again later.")
    
    # Add current timestamp to the request history for the IP
    request_counts[ip].append(current_time)

@app.route('/')
def home():
    return render_template('index.html')

# Additional routes (contact_us, terms, about, privacy, etc.) remain the same

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> str:
    # yt-dlp options with OAuth2 authentication
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'keepvideo': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'oauth2_token': OAUTH_FILE  # OAuth token file path
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            temp_file_path = f"/tmp/{info_dict['id']}.{'webm' if format_type == 'video' else 'mp3'}"

            if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                ydl_opts['outtmpl'] = temp_file_path
                with YoutubeDL(ydl_opts) as ydl_inner:
                    ydl_inner.download([url])
            return temp_file_path

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        raise e

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        temp_file_path = download_media(url, format_type=format_type)
        filename = os.path.basename(temp_file_path)

        with open(temp_file_path, 'rb') as f:
            video_data = f.read()

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
            'oauth2_token': OAUTH_FILE  # Use OAuth token for fetching video info
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

# Cleanup thread to delete old files (optional)
def cleanup_downloads(folder, max_age_seconds=59):
    while True:
        now = time.time()
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        # os.remove(file_path)
                        logging.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {str(e)}")
        time.sleep(600)

cleanup_thread = threading.Thread(target=cleanup_downloads, args=('/tmp',), daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000, channel_timeout=300)
