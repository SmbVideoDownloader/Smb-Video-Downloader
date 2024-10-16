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

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> Tuple[str, str]:
    """Download media and return the temp file path and filename."""
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,  # Path to cookies for authentication
        'quiet': False,  # Set to False to see detailed output for debugging
        'outtmpl': '-',  # Set output to standard output initially
    }

    try:
        # Extract information without downloading
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)  # Get info without downloading
            logging.info(f"Extracted info: {info_dict}")

            # Prepare filename based on video title or ID
            filename = f"{info_dict['id']}.mp4" if format_type == 'video' else f"{info_dict['id']}.mp3"

        # Create a temporary file in /tmp
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4" if format_type == 'video' else ".mp3")
        temp_file_path = temp_file.name  # Store the path of the temporary file
        temp_file.close()  # Close the file so yt-dlp can write to it

        # Update ydl_opts to write to the temp file
        ydl_opts['outtmpl'] = temp_file_path

        # Perform the download
        with YoutubeDL(ydl_opts) as ydl_inner:
            ydl_inner.download([url])

        # Check if the downloaded file is empty
        if os.path.getsize(temp_file_path) == 0:
            logging.error(f"Downloaded file is empty: {temp_file_path}")
            os.remove(temp_file_path)  # Remove the empty file
            raise Exception("Downloaded file is empty.")

        # Return temp file path and filename
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
