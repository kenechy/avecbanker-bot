"""
WSGI configuration for PythonAnywhere
This file tells PythonAnywhere how to run your Flask app

IMPORTANT: Replace all placeholder values with your actual credentials!
"""

import sys
import os

# Add your project directory to the path
# Example: '/home/kenechy/avecbanker-bot'
project_home = '/home/YOUR_USERNAME/avecbanker-bot'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
# Get your bot token from @BotFather on Telegram
os.environ['TELEGRAM_BOT_TOKEN'] = 'YOUR_BOT_TOKEN'

# Get these from your Supabase project: Settings > API
os.environ['SUPABASE_URL'] = 'https://your-project-id.supabase.co'
os.environ['SUPABASE_KEY'] = 'your_supabase_anon_key'

# Your PythonAnywhere webhook URL
os.environ['WEBHOOK_URL'] = 'https://YOUR_USERNAME.pythonanywhere.com/webhook'

# Import the Flask app
from bot_flask import flask_app as application
