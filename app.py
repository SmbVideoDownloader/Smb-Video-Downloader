import os
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO

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

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> BytesIO:
    """Download media and return a BytesIO object."""
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,
        'quiet': False,
        'outtmpl': '-',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio' if format_type == 'audio' else 'FFmpegVideoConvertor',
            'preferedcodec': 'mp3' if format_type == 'audio' else 'mp4',
            'preferredquality': '192',
        }],
        'progress_hooks': [lambda d: logging.info(f"Download progress: {d}")]
    }

    buffer = BytesIO()
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

            # Get the last downloaded file's content
            # Since yt-dlp doesn't directly return the file, we may need a custom postprocessor
            logging.info(f"Finished downloading media: {url}")

            buffer.seek(0)  # Reset buffer pointer
            return buffer
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
        # Download the media to BytesIO
        media_buffer = download_media(url, format_type=format_type)

        # Prepare the response
        filename = f"{url.split('v=')[-1]}.mp4" if format_type == 'video' else f"{url.split('v=')[-1]}.mp3"
        response = Response(
            media_buffer.getvalue(),
            mimetype='video/mp4' if format_type == 'video' else 'audio/mpeg',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

        # Cleanup logic in a separate thread if needed
        def cleanup_buffer():
            time.sleep(100)  # Keep it for 100 seconds before cleanup
            media_buffer.close()  # Close the buffer

        threading.Thread(target=cleanup_buffer).start()

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
            'cookiefile': COOKIES_FILE
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
