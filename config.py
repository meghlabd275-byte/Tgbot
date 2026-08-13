import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', 0))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Bot settings
    MAX_WARNINGS = 3
    DEFAULT_MUTE_TIME = 3600  # 1 hour in seconds
    PURGE_LIMIT = 100  # Maximum messages to purge at once
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.BOT_USERNAME:
            raise ValueError("BOT_USERNAME is required")
        if cls.SUPER_ADMIN_ID == 0:
            raise ValueError("SUPER_ADMIN_ID is required")