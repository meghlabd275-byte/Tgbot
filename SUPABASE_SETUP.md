# Supabase Database Setup Guide

This guide explains how to connect the Telegram Admin Bot to a **Supabase** managed PostgreSQL database.

The bot uses **SQLAlchemy ORM** for all data access. Supabase provides a managed PostgreSQL instance, so switching from local SQLite to Supabase only requires setting environment variables — **no code changes** are needed. Tables (21 of them) are created automatically on first run.

---

## Why Supabase?

| Feature | SQLite (default) | Supabase PostgreSQL |
|---|---|---|
| Setup | Zero-config local file | Cloud-managed |
| Scalability | Single process, local disk | Up to 8 GB / 60 connections (free tier) |
| Backups | Manual `cp` | Automatic daily snapshots |
| Dashboard | None | Full web UI + SQL editor |
| REST API | No | Built-in (PostgREST) |
| Storage | No | File/object storage included |
| Multi-instance | No (file locking) | Yes (connection pooling) |

---

## Step 1: Create a Supabase Project

1. Go to **https://supabase.com** and sign in (GitHub/Google).
2. Click **New Project**.
3. Fill in:
   - **Name**: `telegram-admin-bot` (or any name)
   - **Database Password**: choose a strong password — **save it** (you'll need it)
   - **Region**: pick the one closest to your bot's server
   - **Plan**: Free tier is fine to start
4. Click **Create new project** and wait ~2 minutes for provisioning.

---

## Step 2: Collect Your Credentials

In your Supabase dashboard, go to **Project Settings** (the gear icon):

### A. API keys (Settings → API)
| Field | Where | Env var |
|---|---|---|
| Project URL | top of the page | `SUPABASE_URL` |
| anon public key | "Project API keys" section | `SUPABASE_KEY` |
| service_role key | "Project API keys" section (click `Reveal`) | `SUPABASE_SERVICE_KEY` |

> ⚠️ The **service_role key bypasses Row Level Security**. Never expose it in client-side code. It's optional for the bot (only used by the REST wrapper in `supabase_client.py`).

### B. Database connection (Settings → Database)

You have two equivalent options — pick whichever is easier:

**Option A — Full connection string (preferred):**
1. Go to **Settings → Database → Connection string**.
2. Switch to the **URI** format.
3. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abcdefgh.supabase.co:5432/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with the password from Step 1.
5. Put the whole string in `SUPABASE_DB_URL`. The bot will automatically use the psycopg3 driver (`postgresql+psycopg://`).

**Option B — Connection components:**
From **Settings → Database → Connection info**, copy:
| Field | Env var |
|---|---|
| Host (e.g. `db.abcdefgh.supabase.co`) | `SUPABASE_DB_HOST` |
| Port (`5432`) | `SUPABASE_DB_PORT` |
| Database name (`postgres`) | `SUPABASE_DB_NAME` |
| User (`postgres`) | `SUPABASE_DB_USER` |
| Password (from Step 1) | `SUPABASE_DB_PASSWORD` |

> If you provide `SUPABASE_DB_URL`, the component fields are ignored. You only need one option.

---

## Step 3: Configure the Bot

Edit your `.env` file (copy from `.env.example` if you don't have one):

```env
# --- Required bot config ---
BOT_TOKEN=123456:your-botfather-token
BOT_USERNAME=your_bot_username
SUPER_ADMIN_ID=123456789

# --- Supabase (takes priority over DATABASE_URL when set) ---
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_KEY=eyJhbGciOi...your-anon-key...
SUPABASE_SERVICE_KEY=eyJhbGciOi...your-service-role-key...

# Option A: full connection string
SUPABASE_DB_URL=postgresql://postgres:yourpassword@db.abcdefgh.supabase.co:5432/postgres

# (Optional) pool tuning
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=1800
```

That's it. On the next `python bot.py` start, the bot will:
1. Detect Supabase credentials → use PostgreSQL.
2. Create all 21 tables automatically in your Supabase database.
3. Log `Using PostgreSQL/Supabase database backend`.

---

## Step 4: Verify the Connection

```bash
# Quick config + connection test
python -c "from config import Config; print('DB URL:', Config.get_database_url()[:50]+'...'); print('Supabase enabled:', Config.is_supabase_enabled())"

# Test database + table creation
python -c "from database import db; s=db.get_session(); s.query(db.Chat).all(); s.close(); print('Supabase DB connection OK')"

# REST API health check (optional)
python -c "import supabase_client; print('REST API reachable:', supabase_client.health_check())"

# Full test suite
python test_bot.py && python test_advanced_bot.py && python test_functional.py
```

You can also open the **Supabase dashboard → Table Editor** and you'll see all 21 tables (`chats`, `users`, `admins`, `bans`, `warnings`, `mutes`, `whitelist`, `notes`, `reports`, etc.) populated as the bot runs.

---

## How It Works (Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                      bot.py (PTB v20)                    │
│                          │                               │
│              handlers/*.py (ORM queries)                 │
│                          │                               │
│                  database.py (SQLAlchemy)                │
│                          │                               │
│         create_engine(Config.get_database_url())         │
│                          │                               │
│    ┌─────────────────────┴──────────────────────┐        │
│    │   psycopg2 driver (direct Postgres conn)   │        │
│    └─────────────────────┬──────────────────────┘        │
│                          │                               │
│              Supabase managed PostgreSQL                 │
│     (21 tables auto-created via Base.metadata)           │
└─────────────────────────────────────────────────────────┘

Optional parallel access:
┌─────────────────────────────────────────────────────────┐
│               web_dashboard.py / scripts                 │
│                          │                               │
│             supabase_client.py (REST API)                │
│                          │                               │
│            PostgREST / Storage / Auth                    │
│                          │                               │
│              Supabase managed PostgreSQL                 │
└─────────────────────────────────────────────────────────┘
```

- **`database.py`** → SQLAlchemy ORM over a direct PostgreSQL connection (the bot's primary data path). Connection pooling is configured for managed-database constraints (`pool_pre_ping`, `pool_recycle=1800s`).
- **`supabase_client.py`** → optional thin wrapper around the Supabase REST API (PostgREST) for the web dashboard, backups, and storage. Shares the same database.

Both layers read/write the **same tables** — pick whichever is convenient for a given task.

---

## Connection Pool Tuning

Supabase free tier allows **up to 60 direct connections**. The bot defaults to a conservative pool:

| Env var | Default | Meaning |
|---|---|---|
| `DB_POOL_SIZE` | 5 | Persistent connections kept open |
| `DB_MAX_OVERFLOW` | 5 | Extra connections allowed under load (max = 10 total) |
| `DB_POOL_RECYCLE` | 1800 | Seconds before a connection is recycled (Supabase drops idle conns ~3-5 min; recycle prevents stale-conn errors) |

For a single bot instance the defaults are fine. If you run multiple bot instances or the web dashboard against the same project, lower `DB_POOL_SIZE` to stay under 60 total.

> **Tip:** For higher scale, enable Supabase's **PgBouncer connection pooler** (Settings → Database → Connection pooling) and point `SUPABASE_DB_URL` at the pooler endpoint (port `6543`). Then you can handle hundreds of concurrent clients.

---

## Row Level Security (RLS)

By default, Supabase enables RLS on new tables. Because the bot connects as the `postgres` superuser (via the direct connection string), **RLS does not block the bot** — the ORM queries bypass RLS entirely.

If you want to use the **REST API** (`supabase_client.py`) from a frontend, you should either:
- Use the `SUPABASE_SERVICE_KEY` (bypasses RLS), **or**
- Disable RLS / add policies for the tables you want to expose.

For a backend-only bot, no RLS configuration is needed.

---

## Backups

Supabase takes automatic daily backups on paid plans. For manual / free-tier backups:

```bash
# Via the bot's built-in command (run as admin in any group)
/backup

# Via pg_dump against your Supabase DB
PGPASSWORD=yourpassword pg_dump \
  -h db.abcdefgh.supabase.co \
  -U postgres -d postgres \
  > backup_$(date +%Y%m%d).sql

# Restore
PGPASSWORD=yourpassword psql \
  -h db.abcdefgh.supabase.co \
  -U postgres -d postgres \
  < backup_YYYYMMDD.sql
```

You can also export CSV/JSON for any table directly from the Supabase dashboard → Table Editor → Export.

---

## Migrating from SQLite to Supabase

If you already have data in `bot.db` and want to move it to Supabase:

```bash
# 1. Dump your SQLite data to SQL
#    (install: pip install sqlparse)
python -c "
from database import db, Base
from sqlalchemy import inspect
import json
out = {}
insp = inspect(db.engine)
session = db.get_session()
for t in insp.get_table_names():
    rows = session.execute(f'SELECT * FROM \"{t}\"').fetchall()
    out[t] = [dict(r._mapping) for r in rows]
session.close()
with open('sqlite_export.json','w') as f:
    json.dump(out, f, default=str, indent=2)
print('Exported', len(out), 'tables')
"

# 2. Switch .env to Supabase (so tables get created there)
# 3. Import the JSON into Supabase via the Table Editor or a small script
```

For a fresh start, just configure Supabase and run — tables auto-create empty.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `could not connect to server` / timeout | Check `SUPABASE_DB_HOST`/`SUPABASE_DB_URL` are correct; ensure your server's IP can reach Supabase (no firewall blocking port 5432). Try the pooler endpoint (port 6543). |
| `password authentication failed` | Re-check `SUPABASE_DB_PASSWORD`. In `SUPABASE_DB_URL`, ensure the password is URL-encoded (e.g. `@` → `%40`, `#` → `%23`). |
| `too many connections` | Lower `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, or enable PgBouncer pooler and use port 6543. |
| `connection already closed` / stale errors | Already handled by `pool_pre_ping=True` + `pool_recycle`. If it persists, lower `DB_POOL_RECYCLE` to 300. |
| Tables not appearing in dashboard | Ensure the bot started at least once with Supabase env vars set. Check logs for `Using PostgreSQL/Supabase database backend`. |
| Bot still using SQLite | `Config.is_supabase_enabled()` returns False. Verify `SUPABASE_URL` + `SUPABASE_DB_HOST` + `SUPABASE_DB_PASSWORD` (or `SUPABASE_DB_URL`) are all set and non-empty in the `.env` that's actually loaded (same directory as `bot.py`). |
| `psycopg2` import error | Run `pip install psycopg2-binary` (already in requirements.txt). |

---

## Quick Reference — Minimal `.env` for Supabase

```env
BOT_TOKEN=123456:your-botfather-token
BOT_USERNAME=your_bot_username
SUPER_ADMIN_ID=123456789
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_KEY=eyJhbGciOi...anon-key...
SUPABASE_DB_URL=postgresql://postgres:yourpassword@db.abcdefgh.supabase.co:5432/postgres
```

Then `python bot.py` — done. 🎉
