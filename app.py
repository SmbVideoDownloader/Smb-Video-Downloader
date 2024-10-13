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
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'), # Use video ID instead of full title
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH, # Ensure FFmpeg is located by yt-dlp
        'trim_filenames': 200, # Limit filename length to 200 characters
        'cookiefile': COOKIES_FILE,   # Use cookies for authentication
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            output_file = f"{info_dict['id']}.mp4"
            output_path = os.path.join(temp_dir, output_file)

            # Merge video and audio if necessary
            if format_type == 'video':
                # Using FFmpeg to convert and ensure compatibility
                ffmpeg_command = (
                    f'{FFMPEG_PATH} -i "{file_name}" -c:v libx264 -c:a aac -strict experimental '
                    f'-movflags +faststart "{output_path}"'
                )
                os.system(ffmpeg_command)
            else:
                output_path = file_name # Audio doesn't require merging

            # Read the output file into memory (BytesIO)
            with open(output_path, 'rb') as f:
                file_data = BytesIO(f.read())

            # Clean up the temp directory
            shutil.rmtree(temp_dir)

            return file_data, output_file # Return file data and name

    except Exception as e:
        shutil.rmtree(temp_dir) # Clean up in case of errors
        logging.error(f"Error downloading media: {str(e)}")  # Log the error for debugging
        raise e

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Download the video/audio file and return its path
        output_file = download_media(url, format_type='video')

        # Send the downloaded file to the user
        return send_file(output_file, as_attachment=True, download_name=os.path.basename(output_file))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
