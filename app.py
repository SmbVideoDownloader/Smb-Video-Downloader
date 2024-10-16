import os
import shutil
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, send_file, url_for, after_this_request
from flask_cors import CORS
from yt_dlp import YoutubeDL
from typing import Tuple
import time  # Add this import
import threading  # Add this import

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

# Ensure the DOWNLOAD_FOLDER exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> Tuple[str, str]:
    """
    Download media and return the temporary file path and filename.
    
    Args:
        url (str): The URL of the media to download.
        format_type (str): 'video' or 'audio'.
    
    Returns:
        Tuple[str, str]: A tuple containing the path to the downloaded file and the filename.
    """
    # Define postprocessors based on format_type
    if format_type == 'video':
        postprocessors = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
        suffix = '.mp4'
        mimetype = 'video/mp4'
    else:
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        suffix = '.mp3'
        mimetype = 'audio/mpeg'

    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'noplaylist': True,
        'cookiefile': COOKIES_FILE,  # Path to cookies for authentication
        'quiet': True,  # Reduce yt-dlp output
        'postprocessors': postprocessors,
    }

    try:
        logging.info(f"Starting download for URL: {url} as format: {format_type}")

        # Extract information without downloading
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)  # Get info without downloading
            logging.info(f"Extracted info: {info_dict.get('title', 'No title')}")

            # Prepare filename based on video title or ID
            filename = f"{info_dict['id']}{suffix}"
            logging.info(f"Prepared filename: {filename}")

        # Download to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()  # Close the file so yt-dlp can write to it
        logging.info(f"Downloading to temporary file: {temp_file.name}")

        # Update ydl_opts to write to the temp file
        ydl_opts['outtmpl'] = temp_file.name

        # Perform the download
        with YoutubeDL(ydl_opts) as ydl_inner:
            ydl_inner.download([url])
            logging.info(f"Download completed for file: {temp_file.name}")

        # Check if the file has content
        file_size = os.path.getsize(temp_file.name)
        logging.info(f"Downloaded file size: {file_size} bytes")
        if file_size == 0:
            raise Exception("Downloaded file is empty.")

        # Return temp file path and filename
        return temp_file.name, filename

    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        raise e

# Route to initiate download
@app.route("/download", methods=["POST"])
def download():
    """
    Handle the download request, send the media file to the client, and delete the temp file.
    """
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')  # Assume 'video' if not specified

    if not url:
        logging.warning("No URL provided in the request.")
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the media as a temp file
        temp_file_path, filename = download_media(url, format_type=format_type)

        # Log file size before sending
        file_size = os.path.getsize(temp_file_path)
        logging.info(f"Sending file: {temp_file_path}, size: {file_size} bytes")

        @after_this_request
        def remove_file(response):
            """
            Delete the temporary file after the response is sent.
            """
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

@app.route("/get_video_info", methods=["POST"])
def get_video_info():
    """
    Retrieve video information such as title and thumbnail without downloading the media.
    """
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
    """
    Delete files older than max_age_seconds in the specified folder.
    
    Args:
        folder (str): Path to the folder to clean.
        max_age_seconds (int): Maximum age of files in seconds.
    """
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
