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

### 🔐 Security Features
- **Admin Verification**: Verify admin status by forwarding messages
- **Global Systems**: Cross-chat banning and whitelisting
- **Silent Actions**: Discrete moderation without notifications
- **Anti-Spam Protection**: Basic flood and spam detection

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shahrukh275/Telegram-Bot-.git
   cd Telegram-Bot-
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

### Information Commands
- `/user` - User information
- `/lastactive` - Last activity check
- `/id` - Get user/chat IDs
- `/chatinfo` - Chat statistics

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