import os
import tempfile
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, after_this_request, Response
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO
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

def download_media(url: str) -> Tuple[str, str]:
    """Download media with video and AAC audio (not Opus) and return the temp file path and filename."""

    ydl_opts = {
        'format': 'bestvideo+bestaudio',  # Best video and best audio (separate streams)
        'noplaylist': True,                # Download only a single video
        'outtmpl': '/tmp/%(id)s.f%(format_id)s.%(ext)s',  # Output template with format ID
        'merge_output_format': 'mp4',      # Output will be merged into an MP4 container
        'postprocessors': [
            {
                'key': 'FFmpegMerger',       # Merge video and audio
            }
        ],
        'cookiefile': COOKIES_FILE,        # Use cookies for authenticated access
        'quiet': False,                    # Debugging output
        'overwrites': True                  # Overwrite existing files
    }

    try:
        # Extract the video info to get video_id
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id", "")
            filename = f"{video_id}.mp4"

        # Download the video and audio, merge them
        with YoutubeDL(ydl_opts) as ydl_inner:
            ydl_inner.download([url])

        # Determine the expected video and audio filenames
        video_file = f"/tmp/{video_id}.f303.webm"  # Best video format
        audio_file = f"/tmp/{video_id}.f251.webm"  # Best audio format

        # Construct the temporary merged file path
        temp_file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        
        # Check if the expected files exist before merging
        if os.path.exists(video_file) and os.path.exists(audio_file):
            # Merge files using ffmpeg
            os.system(f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -c:a aac {temp_file_path}")

            # Check if the merging was successful
            if os.path.exists(temp_file_path):
                return temp_file_path, filename
            else:
                raise FileNotFoundError("Merged file was not created.")
        else:
            raise FileNotFoundError("One or more temporary files do not exist.")

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
        # Download the media and get it in-memory as a BytesIO object
        video_data, filename = download_media(url)

        # Send the file as a response, allowing the client to download it
        return Response(
            video_data,
            mimetype='video/mp4' if format_type == 'video' else 'audio/mpeg',
            headers={"Content-Disposition": f"attachment;filename={filename}"}
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
