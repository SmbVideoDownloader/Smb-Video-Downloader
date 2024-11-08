import os
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, Response, abort
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO
from collections import defaultdict, deque
from datetime import datetime, timedelta

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Paths for cookies and OAuth2 files
COOKIES_PATH = '/var/www/v2mp4.com/cookies'
OAUTH_FILE = '/var/www/v2mp4.com/oauth2/oauth2_token.json'

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Rate limiting settings
MAX_REQUESTS = 10  # Maximum requests per IP per minute
TIME_FRAME = 60  # Time frame in seconds (1 minute)
DELAY_TIME = 60  # Delay time in seconds for delayed downloads
request_counts = defaultdict(list)
delayed_downloads = deque()  # Queue for delayed downloads

# List of available cookie files for rotation based on naming pattern
cookie_files = [os.path.join(COOKIES_PATH, f'cookies.txt{i}' if i > 0 else 'cookies.txt') for i in range(10)]
# Adjust the range if you need more than 10 cookie files

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
        logging.warning(f"Rate limit exceeded for IP: {ip}. Adding to delayed queue.")
        
        # Queue the IP with delay
        delayed_downloads.append((ip, request))
        
        # Respond with a rate-limit message
        return jsonify({"error": "Rate limit exceeded. Please wait a minute before continuing."}), 429
    
    # Add current timestamp to the request history for the IP
    request_counts[ip].append(current_time)

@app.route('/')
def home():
    return render_template('index.html')

# Delayed download processing function
def process_delayed_downloads():
    """Process delayed download requests after a specified delay time."""
    while True:
        if delayed_downloads:
            ip, original_request = delayed_downloads.popleft()
            time.sleep(DELAY_TIME)
            logging.info(f"Processing delayed download for IP: {ip}")
            # Trigger the download
            download_media(original_request.get_json()['url'], original_request.get_json().get('format', 'video'))
        time.sleep(1)

# Helper function to download video/audio with cookie rotation
# Helper function to download video/audio with cookie rotation
def download_media(url: str, format_type: str) -> str:
    cookie_index = 0  # Start with the first cookie file
    max_cookies = 20  # Maximum number of cookies available
    success = False

    # Attempt download while rotating through cookie files on error
    while not success and cookie_index <= max_cookies:
        cookie_file_path = f'/var/www/v2mp4.com/cookies/cookies.txt{cookie_index if cookie_index > 0 else ""}'
        
        # yt-dlp options with OAuth2 authentication and the current cookie file
        ydl_opts = {
            'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
            'noplaylist': True,
            'cookiefile': cookie_file_path,
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
                
                # Check if file already exists
                if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) > 0:
                    logging.info(f"Serving existing file: {temp_file_path}")
                    return temp_file_path

                ydl_opts['outtmpl'] = temp_file_path
                with YoutubeDL(ydl_opts) as ydl_inner:
                    ydl_inner.download([url])

                success = True  # Exit loop if download succeeds
                return temp_file_path

        except Exception as e:
            error_message = str(e)
            logging.error(f"Error downloading media with {cookie_file_path}: {error_message}")
            
            # Rotate to the next cookie file if the error is bot-related
            if "Sign in to confirm you’re not a bot" in error_message:
                logging.warning(f"Bot verification error detected with {cookie_file_path}. Trying next cookie file.")
                cookie_index += 1  # Move to the next cookie file
            else:
                # Raise the exception if it's unrelated to bot verification
                raise e

    # If all cookies exhausted and download failed
    raise Exception("All cookie files exhausted. Unable to download media due to bot verification.")


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

        # Read file into memory for streaming
        with open(temp_file_path, 'rb') as f:
            video_data = BytesIO(f.read())

        response = Response(
            video_data.getvalue(),
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
            'cookiefile': cookie_files[0],  # Initial cookie file for info extraction
            'oauth2_token': OAUTH_FILE  # OAuth token file path
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
                        os.remove(file_path)
                        logging.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {str(e)}")
        time.sleep(600)

# Start the cleanup and delayed download processing threads
cleanup_thread = threading.Thread(target=cleanup_downloads, args=('/tmp',), daemon=True)
cleanup_thread.start()
delayed_download_thread = threading.Thread(target=process_delayed_downloads, daemon=True)
delayed_download_thread.start()

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000, channel_timeout=300)
