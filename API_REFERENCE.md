# API Reference

This document provides detailed information about the bot's commands, database structure, and internal APIs.

## Command Reference

### Admin Utility Commands

#### `/fileid`
**Description**: Get file ID from replied media message  
**Usage**: Reply to a media message with `/fileid`  
**Permissions**: Admin only  
**Example**: 
```
User: [sends photo]
Admin: /fileid (reply to photo)
Bot: 📎 File ID: AgACAgIAAxkBAAI...
```

### Chat Management Commands

#### `/activate`
**Description**: Register the current chat with the bot  
**Usage**: `/activate`  
**Permissions**: Telegram admin required  
**Group only**: Yes  

#### `/silence` / `/unsilence`
**Description**: Control who can send messages in the chat  
**Usage**: `/silence` or `/unsilence`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/ua` / `/underattack`
**Description**: Toggle under attack mode (silences chat + kicks new users)  
**Usage**: `/ua` or `/underattack`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/reload`
**Description**: Reload the admin cache  
**Usage**: `/reload`  
**Permissions**: Bot admin  

#### `/debug`
**Description**: Show debug information about chat and bot  
**Usage**: `/debug`  
**Permissions**: Bot admin  

#### `/pin` / `/unpin`
**Description**: Pin or unpin messages  
**Usage**: `/pin` (reply to message) or `/unpin`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/purge`
**Description**: Delete multiple messages  
**Usage**: 
- `/purge` (reply to start message)
- `/purge 10` (delete last 10 messages)
**Permissions**: Bot admin  
**Group only**: Yes  
**Limit**: 100 messages max  

### User Management Commands

#### `/promote` / `/demote`
**Description**: Add or remove admin privileges  
**Usage**: 
- `/promote @username`
- `/promote 123456789`
- `/promote` (reply to user)
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/title`
**Description**: Set custom admin title  
**Usage**: `/title @username Custom Title`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/ban` / `/unban`
**Description**: Ban or unban users from the chat  
**Usage**: 
- `/ban @username [reason]`
- `/unban @username`
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/sban`
**Description**: Silently ban user (no notification)  
**Usage**: `/sban @username [reason]`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/gban` / `/gunban`
**Description**: Globally ban/unban user across all bot chats  
**Usage**: 
- `/gban @username [reason]`
- `/gunban @username`
**Permissions**: Bot admin  

#### `/sgban`
**Description**: Silently globally ban user  
**Usage**: `/sgban @username [reason]`  
**Permissions**: Bot admin  

#### `/banlist`
**Description**: View list of banned users  
**Usage**: `/banlist`  
**Permissions**: Bot admin  
**Group only**: Yes  

#### `/kick` / `/skick` / `/gkick`
**Description**: Kick user from chat(s)  
**Usage**: 
- `/kick @username [reason]`
- `/skick @username` (silent)
- `/gkick @username [reason]` (global)
**Permissions**: Bot admin  

#### `/mute` / `/unmute` / `/smute`
**Description**: Mute/unmute users  
**Usage**: 
- `/mute @username [time] [reason]`
- `/unmute @username`
- `/smute @username [time]` (silent)
**Permissions**: Bot admin  
**Group only**: Yes  
**Time format**: 30s, 5m, 2h, 1d  

### Warning System Commands

#### `/warn` / `/gwarn` / `/swarn`
**Description**: Issue warnings to users  
**Usage**: 
- `/warn @username [reason]`
- `/gwarn @username [reason]` (global)
- `/swarn @username [reason]` (silent)
**Permissions**: Bot admin  
**Auto-ban**: After 3 warnings (configurable)  

#### `/unwarn` / `/resetwarns`
**Description**: Remove warnings from users  
**Usage**: 
- `/unwarn @username` (remove one)
- `/resetwarns @username` (remove all)
**Permissions**: Bot admin  

#### `/warnings`
**Description**: Check user's warning count  
**Usage**: `/warnings @username`  
**Permissions**: Bot admin  

### Whitelist System Commands

#### `/whitelist` / `/gwhitelist`
**Description**: Add user to whitelist (bypass filters)  
**Usage**: 
- `/whitelist @username`
- `/gwhitelist @username` (global)
**Permissions**: Bot admin  

#### `/unwhitelist` / `/gunwhitelist`
**Description**: Remove user from whitelist  
**Usage**: 
- `/unwhitelist @username`
- `/gunwhitelist @username` (global)
**Permissions**: Bot admin  

#### `/whitelisted`
**Description**: View whitelisted users  
**Usage**: `/whitelisted`  
**Permissions**: Bot admin  

#### `/checkwhitelist`
**Description**: Check if user is whitelisted  
**Usage**: `/checkwhitelist @username`  
**Permissions**: Bot admin  

### User Information Commands

#### `/resetuser`
**Description**: Remove all bans, warns, mutes for a user  
**Usage**: `/resetuser @username`  
**Permissions**: Bot admin  

#### `/resetrep`
**Description**: Reset user's reputation to 0  
**Usage**: `/resetrep @username`  
**Permissions**: Bot admin  

#### `/user`
**Description**: View user information and statistics  
**Usage**: 
- `/user @username`
- `/user` (self info)
**Permissions**: None  

#### `/lastactive`
**Description**: Check user's last activity  
**Usage**: `/lastactive @username`  
**Permissions**: Bot admin  

#### `/id`
**Description**: Get user or chat ID  
**Usage**: `/id` or `/id` (reply to user)  
**Permissions**: None  

#### `/chatinfo`
**Description**: Get chat information and statistics  
**Usage**: `/chatinfo`  
**Permissions**: None  

### Verification Commands

#### `/verify`
**Description**: Learn about admin verification  
**Usage**: `/verify`  
**Permissions**: None  

**Admin Verification Process**:
1. Forward any message from a user to the bot in private
2. Bot checks if user is admin in any registered chat
3. Returns detailed verification report

### Help Commands

#### `/help`
**Description**: Show complete command list  
**Usage**: `/help`  
**Permissions**: None  

#### `/start`
**Description**: Welcome message and setup instructions  
**Usage**: `/start`  
**Permissions**: None  

#### `/about`
**Description**: Bot information and features  
**Usage**: `/about`  
**Permissions**: None  

#### `/commands`
**Description**: Quick command reference  
**Usage**: `/commands`  
**Permissions**: None  

## Database Schema

### Tables

#### `chats`
```sql
CREATE TABLE chats (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    is_silenced BOOLEAN DEFAULT FALSE,
    under_attack BOOLEAN DEFAULT FALSE,
    pinned_message_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `users`
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    reputation INTEGER DEFAULT 0,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `admins`
```sql
CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT,
    chat_id BIGINT,
    title VARCHAR(255),
    is_super_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `bans`
```sql
CREATE TABLE bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT,
    chat_id BIGINT,
    banned_by BIGINT,
    reason TEXT,
    is_global BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `warnings`
```sql
CREATE TABLE warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT,
    chat_id BIGINT,
    warned_by BIGINT,
    reason TEXT,
    is_global BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `mutes`
```sql
CREATE TABLE mutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT,
    chat_id BIGINT,
    muted_by BIGINT,
    reason TEXT,
    until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `whitelist`
```sql
CREATE TABLE whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT,
    chat_id BIGINT,
    added_by BIGINT,
    is_global BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token |
| `BOT_USERNAME` | Yes | - | Bot username (without @) |
| `SUPER_ADMIN_ID` | Yes | - | Super admin user ID |
| `DATABASE_URL` | No | `sqlite:///bot.db` | Database connection URL |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Bot Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_WARNINGS` | 3 | Warnings before auto-ban |
| `DEFAULT_MUTE_TIME` | 3600 | Default mute duration (seconds) |
| `PURGE_LIMIT` | 100 | Maximum messages to purge |

## Internal APIs

### Database Manager

#### `DatabaseManager.get_or_create_chat(chat_id, title)`
Create or update chat record.

#### `DatabaseManager.get_or_create_user(user_id, username, first_name, last_name)`
Create or update user record.

#### `DatabaseManager.is_admin(user_id, chat_id)`
Check if user is admin in chat.

#### `DatabaseManager.add_admin(user_id, chat_id, title)`
Add user as admin.

#### `DatabaseManager.remove_admin(user_id, chat_id)`
Remove admin privileges.

#### `DatabaseManager.is_banned(user_id, chat_id)`
Check if user is banned.

#### `DatabaseManager.add_ban(user_id, chat_id, banned_by, reason, is_global)`
Add ban record.

#### `DatabaseManager.remove_ban(user_id, chat_id, is_global)`
Remove ban record.

### Utility Functions

#### `get_user_from_message(update, context)`
Extract user information from command arguments or replied message.

#### `format_user_mention(user)`
Format user mention for display.

#### `parse_time_string(time_str)`
Parse time string (e.g., "1h", "30m") into seconds.

#### `format_time_duration(seconds)`
Format seconds into human-readable duration.

### Decorators

#### `@is_admin_command`
Ensure command is executed by admin.

#### `@is_group_command`
Ensure command is used in group chat.

## Error Handling

### Common Error Responses

| Error | Response |
|-------|----------|
| Not admin | "❌ You need to be an admin to use this command." |
| Private chat only | "❌ This command can only be used in private." |
| Group chat only | "❌ This command can only be used in groups." |
| User not found | "❌ Please specify a user..." |
| Permission denied | "❌ Failed to perform action: insufficient permissions" |

### Exception Handling

All commands include proper exception handling with:
- User-friendly error messages
- Detailed logging for debugging
- Graceful degradation when possible

## Rate Limiting

The bot implements basic rate limiting through:
- Telegram's built-in rate limits
- Command cooldowns (where appropriate)
- Bulk operation limits (e.g., purge limit)

## Security Features

### Admin Verification
- Forward message verification system
- Cross-chat admin status checking
- Scammer protection warnings

### Global Systems
- Global ban enforcement
- Cross-chat whitelist
- Centralized admin management

### Audit Trail
- All actions logged with timestamps
- User activity tracking
- Admin action attribution