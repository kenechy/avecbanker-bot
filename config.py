"""
Configuration for AvecBanker Bot
"""

import os


class Config:
    """Bot configuration"""
    
    # Telegram
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    # Supabase
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    
    # Webhook URL (your PythonAnywhere URL)
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    
    # Timezone
    TIMEZONE = "Asia/Manila"
    
    # Currency
    CURRENCY_SYMBOL = "₱"
    USD_TO_PHP_RATE = 59
