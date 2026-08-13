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

    # ----- Supabase configuration -----
    # The Supabase project URL, e.g. https://abcdefgh.supabase.co
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    # The Supabase anon/public API key (safe for client use)
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    # The Supabase service-role key (server-side only, bypasses RLS).
    # Optional - only needed for admin operations via the REST API.
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')
    # When SUPABASE_URL is set we use the managed Postgres connection string.
    # Provide the full PostgreSQL URL if you have it, otherwise build it from
    # the connection components below.
    SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL', '')
    # Direct connection components (Settings > Database > Connection string)
    SUPABASE_DB_HOST = os.getenv('SUPABASE_DB_HOST', '')
    SUPABASE_DB_PORT = os.getenv('SUPABASE_DB_PORT', '5432')
    SUPABASE_DB_NAME = os.getenv('SUPABASE_DB_NAME', 'postgres')
    SUPABASE_DB_USER = os.getenv('SUPABASE_DB_USER', 'postgres')
    SUPABASE_DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD', '')
    # Connection pool size for the SQLAlchemy engine (Supabase allows up to 60
    # direct connections on the free tier; keep this conservative).
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '5'))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '1800'))  # 30 min

    @classmethod
    def get_database_url(cls) -> str:
        """
        Resolve the effective database URL.

        Priority:
          1. SUPABASE_DB_URL  (full Postgres connection string)
          2. SUPABASE_URL set + component fields  (build postgres URL)
          3. DATABASE_URL     (fallback, e.g. sqlite:///bot.db)
        """
        if cls.SUPABASE_DB_URL:
            # Normalise to the psycopg3 driver if the user pasted a bare
            # postgresql:// or postgresql+psycopg2:// URL.
            url = cls.SUPABASE_DB_URL
            if url.startswith('postgresql://') or url.startswith('postgres://'):
                url = url.replace('postgres://', 'postgresql://', 1)
                url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
            elif url.startswith('postgresql+psycopg2://'):
                url = url.replace('postgresql+psycopg2://', 'postgresql+psycopg://', 1)
            return url
        if cls.SUPABASE_URL and cls.SUPABASE_DB_HOST and cls.SUPABASE_DB_PASSWORD:
            return (
                f"postgresql+psycopg://{cls.SUPABASE_DB_USER}:{cls.SUPABASE_DB_PASSWORD}"
                f"@{cls.SUPABASE_DB_HOST}:{cls.SUPABASE_DB_PORT}/{cls.SUPABASE_DB_NAME}"
            )
        return cls.DATABASE_URL

    @classmethod
    def is_supabase_enabled(cls) -> bool:
        """True when Supabase should be used as the database backend."""
        return bool(cls.SUPABASE_DB_URL or
                    (cls.SUPABASE_URL and cls.SUPABASE_DB_HOST and cls.SUPABASE_DB_PASSWORD))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.BOT_USERNAME:
            raise ValueError("BOT_USERNAME is required")
        if cls.SUPER_ADMIN_ID == 0:
            raise ValueError("SUPER_ADMIN_ID is required")