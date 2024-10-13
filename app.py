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

# Helper function to download video/audio
def download_media(url: str, format_type: str) -> BytesIO:
    temp_dir = tempfile.mkdtemp()
    ydl_opts = {
        'format': 'bestaudio/best' if format_type == 'audio' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),  # Use video ID instead of full title
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,  # Ensure FFmpeg is located by yt-dlp
        'trim_filenames': 200,  # Limit filename length to 200 characters
        'cookiefile': COOKIES_FILE,     # Use cookies for authentication
        'username': 'oauth2',           # Set OAuth2 as the username
        'password': '',                 # OAuth2 doesn't require a password
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            output_file = f"{info_dict['id']}.mp4"
            output_path = os.path.join(temp_dir, output_file)

            # Merge video and audio if necessary
            if format_type == 'video':
                ffmpeg_command = f'{FFMPEG_PATH} -i "{file_name}" -c copy "{output_path}"'
                os.system(ffmpeg_command)
            else:
                output_path = file_name  # Audio doesn't require merging

            # Read the output file into memory (BytesIO)
            with open(output_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Clean up the temp directory
            shutil.rmtree(temp_dir)

            return file_data, output_file  # Return file data and name

    except Exception as e:
        shutil.rmtree(temp_dir)  # Clean up in case of errors
        raise e

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_type = request.form.get('format_type', 'video')  # Default to video

    if not url or not isinstance(url, str) or not url.strip():
        logging.error("Invalid or missing URL provided.")
        return jsonify({"error": "A valid URL is required."}), 400

    temp_dir = None  # Initialize temp_dir

    try:
        logging.info(f"Received download request for URL: {url} with format: {format_type}")
        
        # Download media and get the file path
        file_path, temp_dir = download_media(url, format_type)

        # Check if the file was downloaded correctly
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Stream the file to the user for download
        logging.info(f"Sending file: {file_path}")
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
