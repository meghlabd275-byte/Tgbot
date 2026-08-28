#!/usr/bin/env python3
"""
Setup script for Telegram Admin Bot
"""

import importlib.util
import sys
from pathlib import Path

# Modules that must be importable for the bot to run. The optional database
# drivers (psycopg/PyMySQL/cryptography) are only required for their matching
# DATABASE_URL and are therefore not hard requirements here.
CORE_DEPENDENCIES = [
    ("telegram", "python-telegram-bot"),
    ("sqlalchemy", "SQLAlchemy"),
    ("dotenv", "python-dotenv"),
    ("flask", "Flask"),
]


def _module_available(name: str) -> bool:
    """Return True if `name` can be imported (without importing it)."""
    return importlib.util.find_spec(name) is not None


def create_env_file():
    """Create .env from .env.example if it doesn't exist.

    Returns True when setup may continue (an env file is now present) and
    False only when neither `.env` nor `.env.example` exists.
    """
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        return True

    if env_example.exists():
        print("Creating .env file from template...")
        with open(env_example) as src, open(env_file, "w") as dst:
            dst.write(src.read())
        print("✅ .env file created. Edit it with your bot token and settings.")
        return True

    print("❌ No .env or .env.example file found. Please create one with your bot configuration.")
    return False


def check_dependencies():
    """Check that all core dependencies are installed."""
    missing = [pkg for module, pkg in CORE_DEPENDENCIES if not _module_available(module)]
    if missing:
        print("❌ Missing dependencies: " + ", ".join(missing))
        print("Please run: pip install -r requirements.txt")
        return False
    print("✅ All core dependencies are installed.")
    return True


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
        from database import db  # noqa: F401  (import verifies schema creation)

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
    if sys.version_info < (3, 12):  # noqa: UP036 -- runtime setup aid
        print("❌ Python 3.12 or higher is required.")
        return False

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected.")

    # Check dependencies
    if not check_dependencies():
        return False

    # Create .env file if it doesn't exist yet. We remember whether it existed
    # so we can tell the user to edit it afterwards.
    env_existed = Path(".env").exists()
    if not create_env_file():
        return False

    # Validate configuration (BOT_TOKEN/BOT_USERNAME/SUPER_ADMIN_ID)
    if not test_config():
        if not env_existed:
            print(
                "Hint: edit .env and fill in BOT_TOKEN, BOT_USERNAME and SUPER_ADMIN_ID, then re-run `python setup.py`."
            )
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


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
