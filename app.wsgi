import sys
import os
from app import app as application  # Import the Flask app from your app.py file

# Set the path to your app directory
sys.path.insert(0, '/home/dh_vhkra7/smbvd2mp4.com')

# Optionally, activate virtualenv (if you're using one)
activate_this = '/home/dh_vhkra7/smbvd2mp4.com/venv/bin/activate_this.py'
exec(open(activate_this).read(), {'__file__': activate_this})
