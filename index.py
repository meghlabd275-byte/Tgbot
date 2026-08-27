"""Vercel entrypoint.

Vercel auto-detects Flask from a top-level ``app`` instance in one of the
supported entrypoint files (``app.py``, ``index.py``, ``server.py``,
``main.py``, ``wsgi.py``, ``asgi.py``). This module re-exports the dashboard
app from ``web_dashboard.py`` so Vercel can deploy it.
"""

from web_dashboard import app

__all__ = ["app"]
