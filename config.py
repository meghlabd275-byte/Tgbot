import os
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_SUPER_ADMIN_VALUE_ERROR = (
    "SUPER_ADMIN_ID is required. Set it to your Telegram user ID."
)


def _parse_super_admin_ids():
    """Parse SUPER_ADMIN_ID into a list of owner user ids.

    Supports a single value as well as comma/space separated lists. Invalid
    entries are ignored. Returns an empty list when nothing valid is set.
    """
    raw = str(os.getenv('SUPER_ADMIN_ID', '')).strip()
    if not raw:
        return []
    ids = []
    for token in raw.replace(',', ' ').split():
        if token.lstrip('-').isdigit():
            ids.append(int(token))
    return ids


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')

    # Primary super admin id (first valid entry of SUPER_ADMIN_ID).
    _SUPER_ADMIN_IDS = _parse_super_admin_ids()
    SUPER_ADMIN_ID = _SUPER_ADMIN_IDS[0] if _SUPER_ADMIN_IDS else 0
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
        ids = set(cls._SUPER_ADMIN_IDS)
        for raw in str(cls._EXTRA_SUPER_ADMINS).replace(',', ' ').split():
            raw = raw.strip()
            if raw.lstrip('-').isdigit():
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