import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(override=False)

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


def _int_env(name, default):
    """Read an integer environment variable, failing loudly on bad input."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.error(
            "Environment variable %s = %r is not an integer; using default %r",
            name, raw, default,
        )
        return default


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')

    # Primary super admin id (first valid entry of SUPER_ADMIN_ID).
    _SUPER_ADMIN_IDS = _parse_super_admin_ids()
    SUPER_ADMIN_ID = _SUPER_ADMIN_IDS[0] if _SUPER_ADMIN_IDS else 0
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # --------------------------------------------------------------------
    # Bot settings (overridable via environment variables). The parsing
    # helpers below fail loudly on invalid values at import time, instead
    # of silently trapping the exception via `int(...)` which would raise a
    # ValueError and hide the underlying malformed variable.
    # --------------------------------------------------------------------
    MAX_WARNINGS = _int_env('MAX_WARNINGS', 3)
    DEFAULT_MUTE_TIME = _int_env('DEFAULT_MUTE_TIME', 3600)  # seconds
    PURGE_LIMIT = _int_env('PURGE_LIMIT', 100)  # max messages per purge

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