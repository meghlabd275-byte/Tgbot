# Telegram Admin Bot (Tgbot) — Repository Notes

## Overview
Complete Telegram group admin bot built with python-telegram-bot v20 + SQLAlchemy.
Cloned from `meghlabd275-byte/Tgbot` (branch `main`).

## Environment
- Python 3.13.14
- Install: `pip install -r requirements.txt`
- Run: `python bot.py` (requires BOT_TOKEN, BOT_USERNAME, SUPER_ADMIN_ID env vars / .env)
- DB: SQLite (`bot.db`) by default, or PostgreSQL when `DATABASE_URL` is set
  to a PostgreSQL URL. 21 tables auto-created on import.

## Tests (all must pass)
- `python test_bot.py` — 4 basic tests
- `python test_advanced_bot.py` — 19 advanced tests (imports, tables, definitions)
- `python test_functional.py` — 16 functional tests (exercises real command logic)
- `python test_url_remover.py` — 15 tests (URL remover, join hider, edited-message filters, hidden-hyperlink/entity detection)
- Total: 40 tests. Run all: `python -m pytest test_bot.py test_advanced_bot.py test_functional.py test_url_remover.py -q`

## Critical bugs fixed (commit 26f40a3) — patterns to watch for
1. **`db.<Model>` must exist as DatabaseManager attributes.** Handlers do
   `session.query(db.Chat)`, `db.Admin`, `db.Ban`, etc. The `db` object is a
   `DatabaseManager` *instance*, so model classes must be assigned in
   `DatabaseManager.__init__` (`self.Chat = Chat`, ...). Without this, nearly
   every command crashes with `AttributeError`.
2. **`context.bot.get_chat()` is a coroutine** — must `await` it before reading
   `.permissions`. The anti-pattern `permissions=context.bot.get_chat(chat_id).permissions`
   (no await) passes a coroutine object and breaks mute/captcha/filter/report actions.
3. **`application.run_polling()` is synchronous** in PTB v20 — do NOT wrap in
   `asyncio.run(async main())` + `await run_polling()`. Use a sync `main()` and
   call `application.run_polling(...)` directly. The async wrapper prevents startup.
4. **Handler-defined models** (Note, WordFilter, Report, WelcomeSettings, etc.)
   live in `handlers/*.py`, not on `db`. Import them directly where needed
   (e.g. `from handlers.notes import Note`) rather than `db.Note`.
5. **Register event handlers actually used.** Security logic (under-attack kick,
   global-ban-on-join, bot-added announcement) was in `events.handle_new_member`
   which was imported but never registered — it must live in the registered
   `welcome.handle_new_member_welcome`.
6. **`functools.wraps`** on command decorators so `inspect.getsource`/`__wrapped__`
   work for testing and introspection.

## Architecture
- `bot.py` — entry point, registers all commands + event/callback handlers, including
  an `EditedMessageHandler` (via `filters.UpdateType.EDITED_MESSAGE`) so filters re-run
  on edited messages (prevents bypassing URL/word filters by editing).
- `database.py` — SQLAlchemy models (Chat/User/Admin/Ban/Warning/Mute/Whitelist)
  + DatabaseManager with CRUD methods. `db` is the global instance. 22 tables.
- `handlers/` — 13 modules, each may define its own models on the shared `Base`
  and call `update_*_database()` at import time to create tables.
- `handlers/url_remover.py` — `/removeurls` auto-link-deletion system (mirrors
  @RemoveURLsBot). `URLRemoverSettings` table. Detects URLs/invites in text AND
  captions AND edited messages AND hidden hyperlinks (message entities of type
  text_link/url). Admins exempt. `check_url_remover()` is wired
  into `check_message_filters`.
- `handlers/welcome.py` — welcome/goodbye/captcha PLUS Join-Hider granular toggles
  (`/joinhider joined|left|all|system`) via `delete_joined_msg`/`delete_left_msg`/
  `delete_all_system_msg` columns. `handle_service_message` deletes ALL service
  messages (pins, title/photo changes) when system toggle is on.
- `handlers/filters.py` — word/URL/media/spam filters. `check_message_filters`
  normalizes `update.message or update.edited_message` and checks captions.
  `/lock url` is now functional (deletes messages containing URLs).
- `utils.py` — decorators (`is_admin_command`, `is_group_command`), time parsing,
  user extraction, markdown formatting.
- `web_dashboard.py` — Flask dashboard (separate from bot).

## Git
- Remote: `https://github.com/meglabd275-byte/Tgbot.git` (origin, main branch)
- The provided GITHUB_TOKEN has admin access to this repo but CANNOT create new
  repos (no OAuth scopes / createRepository mutation blocked).

## Database backend
- `config.py`: reads `DATABASE_URL` (defaults to `sqlite:///bot.db`).
- `database.py`: `DatabaseManager()` (no-arg) resolves the URL from
  `Config.DATABASE_URL`; for Postgres it sets `pool_pre_ping=True` and a short
  `pool_timeout` to survive managed databases dropping idle connections.
- Driver: `psycopg[binary]` (psycopg3) - has wheels for Python 3.13, unlike
  psycopg2-binary which fails to build.
- MySQL/MariaDB supported via `mysql+pymysql://` URLs (`PyMySQL` + `cryptography`
  in requirements.txt); `DatabaseManager.__init__` sets `pool_pre_ping`,
  `pool_recycle=3600` for MySQL.

## Feature-parity work (Rose / GroupHelp / WeGroup)
- `handlers/federations.py` — full federation commands (`/fednew`, `/fban`,
  `/fedjoin`, ...) with tables `federations`, `federation_admins`,
  `federation_chats` (chat_id unique), `federation_bans`, `federation_mutes`.
  `enforce_federation_bans()` runs on member join (wired into
  `welcome.handle_new_member_welcome`). NOTE: `handlers/advanced_features.py`
  previously declared duplicate `federation*` tables — removed; federations
  tables must only be declared in `handlers/federations.py`.
- `handlers/connections.py` — Rose-style connections (`/connect`, `/disconnect`,
  `/connection`, `/reconnect`, callback resolution). No DB tables.
- `handlers/approvals.py` — `/approve|unapprove|approved|unapproveall|ignore|…`
  with `Approved`/`Ignored` tables. `db.is_approved()` checks this table and
  approved users bypass flood/filter/url actions.
- `handlers/antiflood.py` — `/antiraid` (on|off|set|status) persists
  `RaidSettings`; `check_raid()` is called from `handle_new_member_welcome`.
- `handlers/admin_commands.py` — `/adminlist`, `/admins`, `/warnmode` (kick|ban|mute|tban).
  `reload_command` resyncs Telegram admins into DB.
- `utils.py` — `is_telegram_admin()` uses `get_chat_administrators` as the
  fallback for `is_admin_command`, so ANY group admin works in ANY group the
  bot is in (auto-registers on first use). `sync_telegram_admins()` bulk-syncs.
- `handlers/filters.py` — `/locktypes`, `/allowlist`, `/unallowlist` command
  verbs exist; check function names before assuming they are absent.

## Owner kill-switch (disable/resume services)
- `database.py` — `DisabledChat` model (`disabled_chats` table: chat_id unique,
  disabled_by, reason, scope, created_at) + `DatabaseManager.disable_chat`,
  `enable_chat`, `is_chat_disabled`, `get_disabled_chats`, `disabled_chat_count`.
  Exposed as `db.DisabledChat`.
- `handlers/services.py` — owner-only `/disable` (`/disableservices`), `/resume`
  (`/resumeservices`), `/disabledgroups`. `resolve_chat_id` accepts an optional
  numeric chat id (so the owner can disable/resume any group from PM).
- `utils.py` — `is_super_admin_command` decorator (only `Config.super_admin_ids()`
  pass; group admins are blocked). `is_admin_command` also blocks all admin
  commands in a disabled group unless the caller is the owner.
- Enforcement points: `bot.handle_all_messages` (top gate), `welcome.py`
  `handle_new_member_welcome` / `handle_left_member_goodbye` /
  `handle_service_message` (early return when `db.is_chat_disabled`).
- Tests: `test_functional.py` covers service-control registration, decorator
  access control, DB round-trip, DisabledChat queryability, and the message gate.
- 49 tests total (`pytest test_bot.py test_advanced_bot.py test_functional.py test_url_remover.py`).

