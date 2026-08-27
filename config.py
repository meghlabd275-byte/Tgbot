import os
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_SUPER_ADMIN_VALUE_ERROR = (
    "SUPER_ADMIN_ID is required. Set it to your Telegram user ID."
)


def _parse_super_admin_id():
    """Parse SUPER_ADMIN_ID, supporting comma-separated lists and single values."""
    raw = os.getenv('SUPER_ADMIN_ID', '')
    if not raw:
        return 0
    raw = str(raw).strip()
    try:
        return int(raw)
    except ValueError:
        # Support comma/space separated lists of admin ids
        ids = [i for i in raw.replace(',', ' ').split() if i]
        if not ids:
            return 0
        try:
            return [int(i) for i in ids][0]
        except (ValueError, IndexError):
            return 0


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
    SUPER_ADMIN_ID = _parse_super_admin_id()
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Bot settings (these can be overridden via environment variables)
    MAX_WARNINGS = int(os.getenv('MAX_WARNINGS', '3'))
    DEFAULT_MUTE_TIME = int(os.getenv('DEFAULT_MUTE_TIME', '3600'))  # seconds
    PURGE_LIMIT = int(os.getenv('PURGE_LIMIT', '100'))  # max messages per purge

    # Extra super admin ids (optional comma/space separated)
    _EXTRA_SUPER_ADMINS = os.getenv('EXTRA_SUPER_ADMIN_IDS', '')

    @classmethod
    def super_admin_ids(cls):
        """Return the set of super-admin (bot owner) user ids."""
        ids = set()
        if cls.SUPER_ADMIN_ID:
            ids.add(int(cls.SUPER_ADMIN_ID))
        for raw in str(cls._EXTRA_SUPER_ADMINS).replace(',', ' ').split():
            raw = raw.strip()
            if raw.isdigit():
                ids.add(int(raw))
        return ids

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.BOT_USERNAME:
            raise ValueError("BOT_USERNAME is required")
        if cls.SUPER_ADMIN_ID == 0:
            raise ValueError(SUPPORTED_SUPER_ADMIN_VALUE_ERROR)