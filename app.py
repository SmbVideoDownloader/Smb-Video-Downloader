import os
import shutil
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
from io import BytesIO

app = Flask(__name__)

# Allow CORS for specific domains
CORS(app, resources={r"/*": {"origins": "https://v2mp4.com"}})

# Path for cookies file for OAuth2
COOKIES_FILE = '/var/www/v2mp4.com/cookies/cookies.txt'

# FFmpeg path
FFMPEG_PATH = "/usr/bin/ffmpeg"  # Correct for Linux

# Set up basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('index.html')  # Serve index.html from the templates directory

# Helper function to download media with yt-dlp
def download_media(url: str, format_type: str) -> str:
    temp_dir = tempfile.mkdtemp()  # Create temp directory for downloading
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'ffmpeg_location': FFMPEG_PATH,
        'cookiefile': COOKIES_FILE,  # Use cookies for auth
        'noplaylist': True,  # Prevent downloading playlists
        'merge_output_format': 'mp4',  # Merge into MP4 for video+audio
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'  # Ensure MP4 output for compatibility
        }],
    }
    
    try:
        logging.debug(f"Attempting to download URL: {url}")
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)

            # Log file name and info
            logging.debug(f"Prepared file name: {file_name}")
            
            final_file = f"{os.path.splitext(file_name)[0]}.mp4" if format_type == 'video' else file_name

            if os.path.exists(final_file):
                logging.debug(f"Final file exists: {final_file}")
                return final_file, temp_dir  # Return file path and temp directory
            else:
                logging.error(f"File not found: {final_file}")
                raise FileNotFoundError(f"Failed to download or merge file: {final_file}")

    except Exception as e:
        logging.error(f"Error during download: {e}")
        shutil.rmtree(temp_dir)  # Clean up in case of error
        raise e  # Raise the error for Flask to handle

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_type = request.form.get('format_type', 'video')  # Default to video

    temp_dir = None  # Initialize temp_dir

    try:
        logging.debug(f"Received request for URL: {url} with format: {format_type}")
        
        # Download media and get the file path
        file_path, temp_dir = download_media(url, format_type)

        # Check if the file was downloaded correctly
        if file_path is None or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Stream the file to the user for download
        logging.debug(f"Sending file: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

    except Exception as e:
        logging.error(f"Error during request processing: {e}")
        # Return the error message to the client
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up temp directory after the download if it was created
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

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

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)  # Run with Waitress
