# Telegram Admin Bot (Tgbot) — Repository Notes

## Overview
Complete Telegram group admin bot built with python-telegram-bot v20 + SQLAlchemy.
Cloned from `meghlabd275-byte/Tgbot` (branch `main`).

## Environment
- Python 3.13.14
- Install: `pip install -r requirements.txt`
- Run: `python bot.py` (requires BOT_TOKEN, BOT_USERNAME, SUPER_ADMIN_ID env vars / .env)
- DB: SQLite (`bot.db`) via SQLAlchemy; 21 tables auto-created on import.

## Tests (all must pass)
- `python test_bot.py` — 4 basic tests
- `python test_advanced_bot.py` — 19 advanced tests (imports, tables, definitions)
- `python test_functional.py` — 16 functional tests (exercises real command logic)

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
- `bot.py` — entry point, registers all 84 commands + event/callback handlers.
- `database.py` — SQLAlchemy models (Chat/User/Admin/Ban/Warning/Mute/Whitelist)
  + DatabaseManager with CRUD methods. `db` is the global instance.
- `handlers/` — 12 modules, each may define its own models on the shared `Base`
  and call `update_*_database()` at import time to create tables.
- `utils.py` — decorators (`is_admin_command`, `is_group_command`), time parsing,
  user extraction, markdown formatting.
- `web_dashboard.py` — Flask dashboard (separate from bot).

## Git
- Remote: `https://github.com/meglabd275-byte/Tgbot.git` (origin, main branch)
- The provided GITHUB_TOKEN has admin access to this repo but CANNOT create new
  repos (no OAuth scopes / createRepository mutation blocked).
