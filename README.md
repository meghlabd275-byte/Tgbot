# Telegram Admin Bot

A comprehensive Telegram bot for advanced group management and moderation with extensive admin features.

## Features

### 🛡️ Admin Utility Commands
- **File ID Extraction**: Get file IDs from media messages for use in other commands
- **Chat Registration**: Register chats for bot management
- **Debug Information**: Comprehensive chat and bot status information

### 💬 Chat Management
- **Silence Mode**: Restrict chat to admin-only communication
- **Under Attack Mode**: Emergency protection mode that silences chat and kicks new users
- **Message Management**: Pin/unpin messages and bulk delete (purge) functionality
- **Admin Cache**: Reload and manage admin permissions cache

### 👥 User Management
- **Promotion System**: Promote/demote users with custom titles
- **Ban System**: Local and global banning with silent options
- **Kick System**: Temporary removal with global capabilities
- **Mute System**: Time-based muting with flexible duration parsing
- **Warning System**: Progressive warning system with auto-ban on limit
- **Whitelist System**: Bypass filters and restrictions for trusted users

### 🔍 User Information & Analytics
- **User Profiles**: Comprehensive user information and statistics
- **Activity Tracking**: Last active timestamps and reputation system
- **Reset Functions**: Clear user violations and reset reputation
- **Chat Statistics**: `/stats` for total/top active members, admin & ban counts
- **Leaderboards**: `/top` for the most active members by message count
- **Invite Links**: `/link` for unique per-user invite links, `/link_stat` for join totals
- **User Commands**: Admins create member-usable `!commands` via `/usercmd`

### 🔐 Security Features
- **Admin Verification**: Verify admin status by forwarding messages
- **Global Systems**: Cross-chat banning and whitelisting
- **Silent Actions**: Discrete moderation without notifications
- **Anti-Spam Protection**: Basic flood and spam detection

### 🛑 Owner Service Controls (super admin only)
- **`/disable` / `/disableservices`** — the bot owner can disable **all** bot services in any group
- **`/resume` / `/resumeservices`** — the owner (and only the owner) can resume a disabled group
- **`/disabledgroups`** — list every group whose services are currently disabled
- Disabling is persisted in the database and enforced across messages, joins/leaves,
  captchas, filters, notes, custom commands, reports and moderation commands.
- Group admins **cannot** disable or resume — this control belongs exclusively to the bot owner.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/meghlabd275-byte/Tgbot.git
   cd Tgbot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**:
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and settings
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Required
BOT_TOKEN=your_bot_token_from_botfather
BOT_USERNAME=your_bot_username
SUPER_ADMIN_ID=your_telegram_user_id

# Optional
DATABASE_URL=sqlite:///bot.db
LOG_LEVEL=INFO
```

### Getting Your Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command and follow instructions
3. Copy the token provided
4. Get your user ID by messaging [@userinfobot](https://t.me/userinfobot)

## Getting Started — Add & Set Up the Bot in a Group

1. **Start the bot** — run `python bot.py` (or deploy it). The bot must be
   online before you add it to a group.

2. **Add the bot to your group**:
   - Open your Telegram group → tap the group name → **Administrators** → **Add
     Admin** → search for your bot's username and add it.
   - Or open a chat with the bot and tap **⋯ → Add to Group / Channel**.

3. **Grant admin permissions** — the bot needs at least:
   - *Change group info* (for welcome/captcha/title changes)
   - *Delete messages* (for purge/delete/filters/URL removal)
   - *Ban users* (for ban/kick/mute)
   - *Invite users via link* (for `/link` and captcha)

4. **Activate the group** — send `/activate` in the group (as an admin). This
   registers the chat and auto-syncs the group's admins into the bot's cache.

5. **Verify it works** — send `/help` to list every command, `/stats` to view
   activity, and `/link` to generate your own invite link.

> **Tip:** the bot auto-registers any group admin who runs an admin command, so
> you can start moderating right away. Only the bot owner (your `SUPER_ADMIN_ID`)
> can use `/disable` / `/resume` to turn all services on or off for a group.

## Commands

### Admin Utility Commands
- `/fileid` - Get file ID from replied media message

### Chat Management
- `/activate` - Register the current chat
- `/silence` / `/unsilence` - Control who can chat
- `/ua` / `/underattack` - Toggle under attack mode
- `/reload` - Reload admin cache
- `/debug` - Show debug information
- `/pin` / `/unpin` - Pin/unpin messages
- `/purge [amount]` - Delete messages

### User Management
- `/promote` / `/demote` - Admin management
- `/title` - Set admin titles
- `/ban` / `/unban` - Ban management
- `/kick` - Kick users
- `/mute` / `/unmute` - Mute management
- `/warn` / `/unwarn` - Warning system
- `/whitelist` / `/unwhitelist` - Whitelist management
- `/gwhitelist` / `/gunwhitelist` - Global whitelist management
- `/whitelisted` - List whitelisted users
- `/checkwhitelist` - Check if a user is whitelisted

### Information Commands
- `/help` - Complete command list
- `/start` - Welcome message and setup guide
- `/about` - Bot information and features
- `/commands` - Quick command reference
- `/user` - User information
- `/lastactive` - Last activity check
- `/id` - Get user/chat IDs
- `/chatinfo` - Chat statistics
- `/stats` / `/statistics` - Total active members, admins, bans, and more
- `/top` / `/leaderboard` - Top active members by message count

### Invite Links
- `/link` - Create your own unique invite link (joins are tracked per link)
- `/link_stat` / `/linkstats` - Show total joins per invite link

### User Commands (admins configure, members use)
- `/usercmd add <name> <response>` - Create a member-usable `!name` command
- `/usercmd del <name>` - Delete a member command
- `/usercmd on|off <name>` - Enable/disable a member command
- `/usercmd setup <name> <response>` - Update a member command's response
- `/usercmd list` - List all member commands
- Members invoke them by typing `!name` in the group

### Global Commands
All user management commands have global variants (prefix with `g`):
- `/gban` / `/gunban` - Global ban management
- `/gkick` - Global kick
- `/gwarn` - Global warnings
- `/gwhitelist` / `/gunwhitelist` - Global whitelist

### Silent Commands
Most moderation commands have silent variants (prefix with `s`):
- `/sban` - Silent ban
- `/skick` - Silent kick
- `/smute` - Silent mute
- `/swarn` - Silent warning

## Command Usage

Commands marked with * support multiple usage formats:

1. **Reply to message**: `/ban` (reply to user's message)
2. **Username**: `/ban @username`
3. **User ID**: `/ban 123456789`

## Time Format

For time-based commands (mute, etc.), use these formats:
- `30s` - 30 seconds
- `5m` - 5 minutes
- `2h` - 2 hours
- `1d` - 1 day

## Admin Verification

Forward any message from a user to the bot in private chat to verify if they're an admin in any chat where the bot is present. This helps prevent admin impersonation scams.

## Database

The bot uses SQLite by default but supports any SQLAlchemy-compatible database. The database stores:

- Chat registrations and settings
- User information and activity
- Admin assignments and titles
- Bans, warnings, and mutes
- Whitelist entries
- Reputation scores

## Security Features

- **Admin-only commands**: Most commands require admin privileges
- **Global ban protection**: Automatically bans globally banned users
- **Under attack mode**: Emergency protection for raids
- **Silent moderation**: Discrete actions without notifications
- **Comprehensive logging**: Full audit trail of all actions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or feature requests:
1. Check existing issues on GitHub
2. Create a new issue with detailed information
3. Contact the bot administrator

## Disclaimer

This bot is designed for legitimate group management purposes. Users are responsible for complying with Telegram's Terms of Service and applicable laws when using this bot.