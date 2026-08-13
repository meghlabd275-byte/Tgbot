"""
Supabase client wrapper.

This module provides optional access to the Supabase REST API (PostgREST),
Storage, and Auth endpoints. The bot's core data layer still runs through
SQLAlchemy ORM (see database.py) against the same managed Postgres database,
so the two layers share one database. This wrapper is useful for:

  - The web dashboard reading/writing data over the REST API
  - Backup/restore operations
  - Storage uploads (e.g. saving backup files, media)
  - Health checks against the Supabase project

It is a *thin* wrapper around the official `supabase-py` client when that
package is available, with graceful fallback to direct HTTP calls so the bot
still runs even if `supabase` is not installed (e.g. when using SQLite only).
"""
import logging
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Return True if Supabase REST credentials are configured."""
    return bool(Config.SUPABASE_URL and Config.SUPABASE_KEY)


def _get_client():
    """
    Return an initialised official supabase-py client, or None if the package
    is missing / credentials are absent.
    """
    if not is_available():
        return None
    try:
        from supabase import create_client, Client
    except ImportError:
        logger.warning(
            "supabase package not installed; REST API wrapper unavailable. "
            "Install with: pip install supabase"
        )
        return None

    key = Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY
    return create_client(Config.SUPABASE_URL, key)


_client: Optional[object] = None


def get_client():
    """Lazily initialise and cache the Supabase client (singleton)."""
    global _client
    if _client is None:
        _client = _get_client()
    return _client


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def fetch_all(table: str, columns: str = "*", limit: int = 1000):
    """
    Fetch rows from a table via the PostgREST API.

    Returns a list of dicts, or an empty list if unavailable.
    """
    client = get_client()
    if client is None:
        return []
    try:
        resp = client.table(table).select(columns).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.error(f"Supabase fetch_all({table}) failed: {e}")
        return []


def insert_row(table: str, row: dict):
    """Insert a single row and return the inserted record, or None."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = client.table(table).insert(row).execute()
        return (resp.data or [None])[0]
    except Exception as e:
        logger.error(f"Supabase insert_row({table}) failed: {e}")
        return None


def delete_rows(table: str, filters: dict):
    """Delete rows matching all filter equality conditions."""
    client = get_client()
    if client is None:
        return 0
    try:
        query = client.table(table).delete()
        for col, val in filters.items():
            query = query.eq(col, val)
        resp = query.execute()
        return len(resp.data or [])
    except Exception as e:
        logger.error(f"Supabase delete_rows({table}) failed: {e}")
        return 0


def health_check() -> bool:
    """
    Ping the Supabase REST API. Returns True if reachable.
    """
    if not is_available():
        return False
    try:
        import requests
        url = f"{Config.SUPABASE_URL}/rest/v1/"
        headers = {"apikey": Config.SUPABASE_KEY}
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return False


def upload_file(bucket: str, path: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload bytes to a Supabase Storage bucket. Returns True on success."""
    client = get_client()
    if client is None:
        return False
    try:
        client.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type})
        return True
    except Exception as e:
        logger.error(f"Supabase upload_file({bucket}/{path}) failed: {e}")
        return False


def download_file(bucket: str, path: str):
    """Download a file from a Supabase Storage bucket. Returns bytes or None."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = client.storage.from_(bucket).download(path)
        return resp
    except Exception as e:
        logger.error(f"Supabase download_file({bucket}/{path}) failed: {e}")
        return None
