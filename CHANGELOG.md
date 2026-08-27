# Changelog

All notable changes to the Telegram Admin Bot will be documented in this file.

## [1.7.0] - 2026-08-27

### Added - Live clone bots (owner fleet)
- **Fleet registry** (`database.py`) — `BotInstance` table stores every cloned
  bot (token, username, bot id, status `active|paused|disabled`); `GroupMembership`
  table stores every group each fleet bot is in. New CRUD methods:
  `register_bot_instance`, `get_bot_instances`, `get_bot_instance_by_id/token`,
  `update_bot_instance`, `set_bot_status`, `delete_bot_instance`,
  `count_bot_instances`, `record_group_membership`, `record_fleet_membership`,
  `remove_group_membership`, `remove_fleet_membership`, `get_fleet_groups`,
  `get_groups_for_bot`.
- **Clone supervisor** (`handlers/clonebot.py`) — each clone runs the exact same
  handler pipeline as the main bot inside a dedicated thread with its own asyncio
  event loop (Python 3.13 compatible). `start_clone_supervisor()` auto-starts
  every `active` clone at boot. Lifecycle controls: `start_clone`, `stop_clone`,
  `set_clone_status` (start/stop/pause/resume/enable/disable), all fully
  implemented and tested. Invalid/revoked tokens are marked `disabled`.
- **Owner fleet commands** (`handlers/owner.py`):
  - `/groups` — list every Telegram group using the fleet with days of usage.
  - `/clone` — interactive live-clone registration (bot token + username only,
    no deployment). Validates via `getMe`, starts the clone immediately and
    re-syncs group memberships fleet-wide.
  - `/clone_bots` — list all clone bots with live status.
  - `/bot <start|stop|pause|resume|enable|disable|status> <id|@username>` — manage clones.
  - `/botdel <id|@username>` — permanently remove a clone.
  - `/commands` now also shows the full super-admin documentation to the owner.
- **Fleet membership tracking** (`handlers/events.py` and `handlers/owner.py`) —
  when a fleet bot (main or clone) is added to a group, every known bot in the
  fleet is recorded as serving that group; removals clean up the registry.
  All enrichment is driven by the owner's Telegram commands (no external dashboard).

## [1.6.0] - 2026-08-27

### Added - Quick replies, welcome buttons, and greeting cleanup
- **Quick replies** (`handlers/quick_replies.py`) — admin-configured auto-replies:
  - **Contract addresses**: `/setcontract <network> <address>` registers a CA;
    when a member types `ca` (or `CA`/`cA`/`Ca`, "contract", "contract address")
    the bot replies with every configured address and its network. Managed with
    `/delcontract` and `/contracts`.
  - **Keyword links**: `/setkeywordlink <keyword> <url> [text]` replies with an
    inline button when a member's message contains the keyword (e.g. `website`,
    `contact`, `proposal`). Managed with `/delkeywordlink` and `/keywordlinks`.
  - **Greeting auto-delete**: `/greetingfilter on|off` deletes throwaway
    greetings ("hi", "hello", "hey", ...) for non-admins.
- **Welcome message inline buttons** (`handlers/welcome.py`):
  - `/setwelcomebutton <label> <url>` attaches one inline link button to the
    welcome message (also supports the legacy JSON `welcome_buttons` column).
  - `/welcomebuttons` shows the current button, `/delwelcomebutton` removes it.
- **Welcome auto-delete**: `/welcomedelete [seconds|on|off]` auto-deletes the
  welcome message after the configured delay (60 seconds by default). The
  `WelcomeSettings.can_delete_welcome` flag enables it; `delete_welcome` now
  defaults to 60 when unset.
- All new commands are documented in `/help` and `/commands`.

### Tests
- Added regression tests for quick-reply tables+registration, contract-address
  lookup, keyword-link lookup, welcome button/auto-delete columns, and removed
  dead `get_chat` code. Suite now collects 58 tests.

## [1.5.1] - 2026-08-27

### Fixed - Critical startup and correctness bugs
- **Bot could not start on Python 3.13.** `python-telegram-bot>=21.4,<22` is now
  required; PTB 20.x/21.2/21.3 crashed at `Application.Builder().build()` with
  `AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb'`.
- **Custom commands never fired.** `/addcmd`-defined commands were stored in the
  DB but no fallback command handler ran for unmatched `/command` messages.
  Added a `MessageHandler(filters.COMMAND, handle_custom_command)` after all
  `CommandHandler`s and before the `~filters.COMMAND` text pipeline. Also made
  `handle_custom_command` strip a bot-username suffix (`/cmd@BotName`) and made
  `/addcmd`/`/delcmd` tolerate a leading `/` or `!`.
- **Startup/event crash on non-existent enum.** Removed references to the
  non-existent `ChatMemberStatus.KICKED` (Telegram reports bans and kicks both as
  `BANNED == 'kicked'`), which raised `AttributeError` in the member-update path.
- **Duplicate bot-added greeting.** The bot announced itself twice when added to
  a group (once via the NEW_CHAT_MEMBERS welcome path and once via the
  MY_CHAT_MEMBER handler). The MY_CHAT_MEMBER handler now only registers the chat
  and syncs admins.
- **`/reports autodelete on|off` was documented but missing.** Implemented the
  subcommand and wired the `auto_delete_reports` setting into report-command
  deletion (previously the command was always deleted regardless of the setting).

### Tests
- Added regression tests for each fix (custom-command fallback, KICKED removal,
  single-source bot greeting, `/reports autodelete`). The combined suite now
  collects 53 tests.

## [1.5.0] - 2026-08-27

### Added - Invite links, user commands, and chat statistics
- **Invite links** (`handlers/invite_links.py`):
  - `/link` — creates a unique, per-user invite link for the group (named links
    so joins can be attributed back to the creator).
  - `/link_stat` (alias `/linkstats`) — shows total joins per invite link; admins
    see every link, members only their own.
  - Join attribution via Telegram's `chat_member` update `invite_link.name`,
    recorded in the new `invite_links` and `link_joins` tables.
- **User commands** (`handlers/user_commands.py`):
  - `/usercmd` — group admins can `add`, `del`, `on`/`off`, `setup`, and `list`
    member-usable `!name` commands (start/setup/stop controls).
  - Members invoke a command by typing `!name`; only admin-enabled commands run.
  - New `user_commands` table.
- **Chat statistics** (`handlers/stats.py`):
  - `/stats` (alias `/statistics`) — total members, active members, total
    messages, admin/ban/warning/mute/whitelist counts, plus a top-5 leaderboard.
  - `/top` (alias `/leaderboard`) — top-15 most active members by message count.
  - Persistent per-chat message counting in the new `message_counts` table
    (incremented from the message pipeline, survives restarts).

### Changed - Documentation
- README.md, README_COMPLETE.md, FEATURE_LIST.md, ADVANCED_FEATURES.md,
  API_REFERENCE.md and CHANGELOG.md updated with the new commands and tables.

### Tests
- All existing test suites remain green (63 tests).

## [1.4.0] - 2026-08-27

### Added - Owner kill-switch (disable / resume all services)
- New `disabled_chats` table plus `DatabaseManager.disable_chat` / `enable_chat` /
  `is_chat_disabled` / `get_disabled_chats` / `disabled_chat_count`.
- New owner-only commands:
  - `/disable` (alias `/disableservices`) `[chat_id]` — disable ALL bot services in a group.
  - `/resume` (alias `/resumeservices`) `[chat_id]` — resume all services (owner only).
  - `/disabledgroups` — list all groups whose services are currently disabled.
- New `@is_super_admin_command` decorator: only the bot owner
  (`SUPER_ADMIN_ID` / `EXTRA_SUPER_ADMIN_IDS`) can run these. Group admins **cannot**
  resume a disabled group.
- Enforcement wired into:
  - `handle_all_messages` (message / filter / note / flood pipeline)
  - `handle_new_member_welcome`, `handle_left_member_goodbye`, `handle_service_message`
  - `@is_admin_command` decorator (blocks all admin commands in a disabled group)
- `silence` and `activate` now use the admin permission decorator (previously
  unsilenced/unauthorized activation was possible in some cases).

### Changed - Documentation & configuration
- `.env.example` documents SQLite / PostgreSQL / MySQL URLs and extra owner IDs.
- All Markdown docs refreshed (README.md, README_COMPLETE.md, FEATURE_LIST.md,
  ADVANCED_FEATURES.md, API_REFERENCE.md, DEPLOYMENT.md, PROJECT_SUMMARY.md, CHANGELOG.md).

### Tests
- 6 new tests: owner service-control registration, super-admin decorator access
  control, disable/resume DB round-trip, DisabledChat model queryability, and
  message-pipeline gate.
- Total: 49 tests passing.

## [1.3.0] - 2026-08-13

### Enhanced - URL Remove Bot (full parity with @RemoveURLsBot)
- URL detection now inspects **message entities** (`text_link` and `url` types), so it
  catches URLs **hidden behind hyperlinks** (e.g. "click here" -> https://evil.com).
  Previously a user could bypass URL removal by hiding the URL in a text_link entity.
- New `message_has_link(message)` helper checks text, caption, AND entities.
- `check_url_remover` now uses entity-aware detection in all modes (remove_urls,
  remove_invites, remove_all_links).

### Enhanced - Join Hider Bot (full parity with @joinhider_bot)
- New `/joinhider system on|off` - deletes **ALL** service messages (pinned-message
  notifications, group-name changes, photo changes, group-created messages, etc.).
- New `delete_all_system_msg` column on `WelcomeSettings`.
- New `handle_service_message` handler registered with `filters.StatusUpdate.ALL`
  (excluding NEW_CHAT_MEMBERS and LEFT_CHAT_MEMBER, which have their own granular
  handlers).

### Tests
- 4 new tests: hidden text_link URL detection, remove_all_links hidden-link
  detection, joinhider system option, handle_service_message existence.
- Total: 40 tests passing.

## [1.2.0] - 2026-08-13

### Added - URL Remove Bot features (mirrors @RemoveURLsBot / @RemoveSpamLinkBot / @RemoveHyperlinkBot)
- New `/removeurls` command family for automatic deletion of messages containing links
  - `/removeurls on|off` - toggle auto-removal of all web URLs (http(s)://, www., bare domains)
  - `/removeurls invites on|off` - also remove Telegram t.me invite / joinchat links
  - `/removeurls all on|off` - remove every link type (URLs + invites + @channel mentions)
  - `/removeurls warn on|off` - also warn the sender after deleting
  - `/removeurls status` - show current settings
- New `handlers/url_remover.py` module with `URLRemoverSettings` table
- Link detection now works on **photo/video captions** (not just message text)
- Link detection now works on **edited messages** (prevents bypassing filters by editing)
- Detects `t.me/`, `t.me/joinchat/`, `t.me/+hash`, and bare domains (e.g. `example.com`)
- Admins and whitelisted users are always exempt

### Added - Join Hider features (mirrors @joinhider_bot)
- New `/joinhider` command with granular toggles for hiding system service messages
  - `/joinhider joined on|off` - hide "X joined the group" service messages
  - `/joinhider left on|off` - hide "X left the group" service messages
  - `/joinhider all on|off` - hide both join and leave service messages
  - `/joinhider` (no args) - show current join-hider settings
- New `delete_joined_msg` and `delete_left_msg` columns on `WelcomeSettings` table
- `/cleanservice` retained as legacy master toggle and now cross-references `/joinhider`

### Added - We Group Bot features (group management)
- Extended `/help` with complete, categorized command listing for all 50+ commands
- Existing welcome/goodbye/captcha/rules/stats features documented and verified

### Fixed
- `/lock url` now actually deletes messages containing URLs (previously set a lock that was never checked)
- `check_message_filters`, `check_word_filters`, `check_url_filters`, `check_spam_patterns`, and `check_media_filters` now correctly inspect message **captions** in addition to text
- Filter pipeline no longer crashes on edited messages (`update.message` is None for edits)
- `apply_filter_action` now uses `update.effective_message` so it works for both regular and edited messages

### Tests
- New `test_url_remover.py` — 11 tests covering URL detection, caption handling, edited-message handling, admin exemption, invite removal, join-hider schema, and command registration
- Total: 36 tests passing (25 original + 11 new)

## [1.1.0] - 2025-06-15

### Added
- PostgreSQL backend support via `DATABASE_URL` (falls back to local SQLite)

## [1.0.0] - 2025-06-15

### Added
- **Complete Bot Implementation**: Full-featured Telegram admin bot with all specified commands
- **Admin Utility Commands**:
  - `/fileid` - Get file ID from media messages
- **Chat Management Commands**:
  - `/activate` - Register chat with bot
  - `/silence`/`/unsilence` - Control chat permissions
  - `/ua`/`/underattack` - Emergency protection mode
  - `/reload` - Refresh admin cache
  - `/debug` - Comprehensive debug information
  - `/pin`/`/unpin` - Message pinning system
  - `/purge` - Bulk message deletion
- **User Management System**:
  - `/promote`/`/demote` - Admin management
  - `/title` - Custom admin titles
  - `/ban`/`/unban` - Local banning system
  - `/sban` - Silent banning
  - `/gban`/`/gunban` - Global banning system
  - `/sgban` - Silent global banning
  - `/banlist` - View banned users
  - `/kick`/`/skick`/`/gkick` - Kicking system
  - `/mute`/`/unmute`/`/smute` - Muting system with time parsing
- **Warning System**:
  - `/warn`/`/gwarn`/`/swarn` - Warning system
  - `/unwarn`/`/resetwarns` - Warning management
  - `/warnings` - Check warning status
  - Auto-ban on warning limit
- **Whitelist System**:
  - `/whitelist`/`/gwhitelist` - Add to whitelist
  - `/unwhitelist`/`/gunwhitelist` - Remove from whitelist
  - `/whitelisted` - View whitelisted users
  - `/checkwhitelist` - Check whitelist status
- **User Information Commands**:
  - `/resetuser` - Clear all violations
  - `/resetrep` - Reset reputation
  - `/user` - User information and statistics
  - `/lastactive` - Activity tracking
  - `/id` - Get user/chat IDs
  - `/chatinfo` - Chat statistics
- **Admin Verification System**:
  - Forward message verification
  - Cross-chat admin checking
  - Scammer protection
- **Help System**:
  - `/help` - Complete command reference
  - `/start` - Welcome and setup
  - `/about` - Bot information
  - `/commands` - Quick reference
- **Database System**:
  - SQLite default with SQLAlchemy ORM
  - Support for PostgreSQL, MySQL
  - Comprehensive data models
  - Automatic migrations
- **Security Features**:
  - Admin-only command protection
  - Global ban enforcement
  - Silent moderation options
  - Comprehensive audit logging
- **Event Handling**:
  - New member processing
  - Under attack mode protection
  - Chat member updates
  - Message filtering
- **Configuration System**:
  - Environment variable configuration
  - Flexible settings
  - Validation and error handling
- **Documentation**:
  - Complete README with setup instructions
  - API reference documentation
  - Deployment guide
  - Comprehensive examples
- **Testing**:
  - Unit tests for core functionality
  - Integration tests
  - Setup validation
- **Optional Features**:
  - Web dashboard for monitoring
  - Health check endpoints
  - Statistics API

### Technical Features
- **Modular Architecture**: Organized handler modules for maintainability
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Logging**: Detailed logging for debugging and monitoring
- **Rate Limiting**: Built-in protection against spam and abuse
- **Time Parsing**: Flexible time format support (30s, 5m, 2h, 1d)
- **User Mention Formatting**: Smart user mention handling
- **Command Flexibility**: Multiple command usage formats (reply, username, ID)
- **Database Optimization**: Efficient queries and connection management
- **Async Support**: Full async/await implementation for performance

### Security
- **Admin Verification**: Prevent admin impersonation
- **Global Systems**: Cross-chat protection
- **Silent Actions**: Discrete moderation
- **Audit Trail**: Complete action logging
- **Permission Checks**: Strict access control

### Deployment
- **Multiple Options**: Local, VPS, Docker, Cloud platforms
- **Environment Configuration**: Secure credential management
- **Health Monitoring**: Built-in health checks
- **Backup Support**: Database backup strategies
- **Scaling**: Horizontal and vertical scaling support

### Documentation
- **Complete Setup Guide**: Step-by-step installation
- **Command Reference**: Detailed command documentation
- **API Documentation**: Internal API reference
- **Deployment Guide**: Production deployment strategies
- **Troubleshooting**: Common issues and solutions