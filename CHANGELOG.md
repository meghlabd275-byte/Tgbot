# Changelog

All notable changes to the Telegram Admin Bot will be documented in this file.

## [1.2.0] - 2026-08-13

### Added — URL Remove Bot features (mirrors @RemoveURLsBot / @RemoveSpamLinkBot / @RemoveHyperlinkBot)
- New `/removeurls` command family for automatic deletion of messages containing links
  - `/removeurls on|off` — toggle auto-removal of all web URLs (http(s)://, www., bare domains)
  - `/removeurls invites on|off` — also remove Telegram t.me invite / joinchat links
  - `/removeurls all on|off` — remove every link type (URLs + invites + @channel mentions)
  - `/removeurls warn on|off` — also warn the sender after deleting
  - `/removeurls status` — show current settings
- New `handlers/url_remover.py` module with `URLRemoverSettings` table
- Link detection now works on **photo/video captions** (not just message text)
- Link detection now works on **edited messages** (prevents bypassing filters by editing)
- Detects `t.me/`, `t.me/joinchat/`, `t.me/+hash`, and bare domains (e.g. `example.com`)
- Admins and whitelisted users are always exempt

### Added — Join Hider features (mirrors @joinhider_bot)
- New `/joinhider` command with granular toggles for hiding system service messages
  - `/joinhider joined on|off` — hide "X joined the group" service messages
  - `/joinhider left on|off` — hide "X left the group" service messages
  - `/joinhider all on|off` — hide both join and leave service messages
  - `/joinhider` (no args) — show current join-hider settings
- New `delete_joined_msg` and `delete_left_msg` columns on `WelcomeSettings` table
- `/cleanservice` retained as legacy master toggle and now cross-references `/joinhider`

### Added — We Group Bot features (group management)
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
- Supabase managed PostgreSQL backend (see `SUPABASE_SETUP.md`)
  - `config.py` resolves DB URL with priority: `SUPABASE_DB_URL` > Supabase components > `DATABASE_URL`
  - `supabase_client.py` REST wrapper, degrades gracefully without credentials
  - Falls back to local SQLite when Supabase is not configured

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