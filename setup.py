#!/usr/bin/env python3
"""
Setup script for Telegram Admin Bot
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from template...")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ .env file created. Please edit it with your bot token and settings.")
        return False
    elif not env_file.exists():
        print("❌ No .env file found. Please create one with your bot configuration.")
        return False
    return True

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import telegram
        import sqlalchemy
        import aiosqlite
        import dotenv
        import pytz
        print("✅ All dependencies are installed.")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def test_config():
    """Test if configuration is valid"""
    try:
        from config import Config
        Config.validate()
        print("✅ Configuration is valid.")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def setup_database():
    """Initialize the database"""
    try:
        from database import db
        print("✅ Database initialized successfully.")
        return True
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False

def main():
    """Main setup function"""
    print("🤖 Telegram Admin Bot Setup")
    print("=" * 30)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected.")
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Test configuration
    if not test_config():
        return False
    
    # Setup database
    if not setup_database():
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your bot token and settings")
    print("2. Run the bot with: python bot.py")
    print("3. Add the bot to your Telegram group")
    print("4. Make it an admin and use /activate")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)