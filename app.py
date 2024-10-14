import os
import shutil
import tempfile
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
from yt_dlp import YoutubeDL

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
DOWNLOAD_FOLDER = tempfile.mkdtemp()

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> (str, str):
    """Download media and return the path and filename."""
    temp_dir = tempfile.mkdtemp(dir=DOWNLOAD_FOLDER)  # Create subdir in DOWNLOAD_FOLDER
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),  # Use video ID instead of full title
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,  # Ensure FFmpeg is located by yt-dlp
        'trim_filenames': 200,  # Limit filename length to 200 characters
        'cookiefile': COOKIES_FILE,   # Use cookies for authentication
        'quiet': True,  # Reduce yt-dlp output
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Convert to mp4
        }],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            if format_type == 'video':
                output_file = f"{info_dict['id']}.mp4"
            else:
                output_file = f"{info_dict['id']}.mp3"
            output_path = os.path.join(temp_dir, output_file)
        
        # Ensure the output file exists
        if not os.path.exists(output_path):
            logging.error(f"Output file not found: {output_path}")
            raise FileNotFoundError("Failed to download the file.")

        return output_path, output_file

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)  # Clean up in case of errors
        logging.error(f"Error downloading media: {str(e)}")  # Log the error for debugging
        raise e

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'video')  # Assume 'video' if not specified

    if not url:
        logging.warning("No URL provided in the request.")
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the media/audio file and return its path and filename
        output_file_path, filename = download_media(url, format_type=format_type)
        logging.info(f"Media downloaded successfully: {output_file_path}")

        # Create a unique identifier for the file
        download_id = os.path.basename(tempfile.mkstemp()[1])  # Generate a unique temp name
        download_url = url_for('download_file', download_id=download_id, _external=True)

        # Move the file to a public location with the download_id
        public_path = os.path.join(DOWNLOAD_FOLDER, download_id)
        shutil.move(output_file_path, public_path)
        logging.info(f"File moved to public path: {public_path}")

        # Return the download URL and filename
        return jsonify({'file_url': download_url, 'filename': filename})

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
