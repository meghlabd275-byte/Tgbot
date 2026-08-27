# 🤖 Ultimate Telegram Admin Bot

**The most comprehensive Telegram admin bot with ALL features from popular bots + unique exclusive features!**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue.svg)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Features](https://img.shields.io/badge/Features-100+-brightgreen.svg)](#features)

## 🌟 What Makes This Bot Special

- **🔥 100+ Features** - Everything from basic moderation to advanced anti-spam
- **🛡️ Unique Admin Verification** - Prevent scammer impersonation (exclusive feature)
- **🌐 Web Dashboard** - Real-time monitoring and management interface
- **🔗 Global Protection** - Cross-chat ban/whitelist system
- **📱 Modern Interface** - Interactive buttons and user-friendly responses
- **⚡ High Performance** - Async implementation with flood protection
- **🔧 Fully Customizable** - Open source with modular architecture
- **📊 Complete Analytics** - Detailed statistics and reporting

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/meghlabd275-byte/Tgbot.git
cd Telegram-Bot-

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your bot
cp .env.example .env
# Edit .env with your bot token and settings

# 4. Test the setup
python test_bot.py

# 5. Run the bot
python bot.py

# 6. Optional: Start web dashboard
python web_dashboard.py
```

## 📋 Complete Feature List

### 🛠️ [Admin] Utility Commands
- `/fileid` - Get File ID of media messages

### 💬 [Admin] Chat Management  
- `/activate` - Register the current chat
- `/silence` / `/unsilence` - Control who can chat
- `/ua` / `/underattack` - Toggle under attack mode
- `/reload` - Reload admin cache
- `/debug` - Print debug information
- `/pin` / `/unpin` - Pin/unpin messages
- `/purge [amount]` - Delete messages

### 👥 [Admin] User Management
- `/promote` / `/demote` - Admin management *
- `/title` - Add title to user *
- `/ban` / `/sban` / `/gban` / `/sgban` - Banning system *
- `/unban` / `/gunban` - Unbanning system *
- `/banlist` - View banned users
- `/kick` / `/skick` / `/gkick` - Kicking system *
- `/mute` / `/unmute` / `/smute` - Muting system *

### ⚠️ [Admin] Warning System
- `/warn` / `/gwarn` / `/swarn` - Warning system *
- `/unwarn` / `/resetwarns` - Warning management *
- `/warnings` - Check warning status
- Auto-ban on warning limit (configurable)

### ✅ [Admin] Whitelist System
- `/whitelist` / `/gwhitelist` - Add to whitelist *
- `/unwhitelist` / `/gunwhitelist` - Remove from whitelist *
- `/whitelisted` - View whitelisted users
- `/checkwhitelist` - Check whitelist status

### 📊 [Admin] User Information
- `/resetuser` - Remove all violations from user *
- `/resetrep` - Reset user reputation *
- `/user` - View user information *
- `/lastactive` - Check user's last activity *
- `/id` - Get user or chat ID
- `/chatinfo` - Get chat information

### 🔰 [Admin] Approvals & Ignores
- `/approve` - Approve a user (immune to automated actions)
- `/unapprove` - Remove a user's approval
- `/approval` - Check a user's approval status *
- `/approved` - List all approved users
- `/unapproveall` - Remove every approval in the chat
- `/ignore` - Ignore a user's commands
- `/unignore` - Remove a user from the ignore list
- `/ignored` - List all ignored users

### 🌊 Anti-Spam & Flood Protection
- `/setflood <number>` - Set flood protection limit
- `/setfloodmode <action>` - Set flood action (mute/kick/ban)
- `/flood` - Show current flood settings
- Real-time flood detection and automatic action
- Configurable time windows and actions
- Admin and whitelist exemptions

### 🔍 Advanced Filters System
- `/addfilter <word> <action>` - Add word filter with action
- `/removefilter <word>` - Remove word filter
- `/filters` - List all active filters
- `/lock <type>` - Lock message types (url/photo/video/document/sticker/voice/etc)
- `/unlock <type>` - Unlock message types
- `/locks` - Show currently locked types
- `/antispam on|off` - Toggle anti-spam protection
- Automatic spam pattern detection
- URL filtering and suspicious link detection
- Media type restrictions
- Regex filter support

### 👋 Welcome & Goodbye System
- `/setwelcome <message>` - Set custom welcome message with variables
- `/setgoodbye <message>` - Set custom goodbye message
- `/welcome on|off` - Toggle welcome messages
- `/goodbye on|off` - Toggle goodbye messages
- `/captcha on|off` - Toggle captcha verification for new users
- `/cleanservice on|off` - Auto-delete join/leave service messages
- Welcome message variables: `{first}`, `{last}`, `{fullname}`, `{username}`, `{mention}`, `{id}`, `{chatname}`, `{count}`
- Math captcha system with auto-kick for failed attempts
- Customizable captcha timeout
- Media welcome messages support

### 📝 Notes & Rules System
- `/save <name> <content>` - Save text or media notes
- `/get <name>` - Retrieve saved notes
- `/clear <name>` - Delete notes
- `/notes` - List all saved notes
- `#notename` - Quick note access shortcut
- `/setrules <text>` - Set chat rules
- `/rules` - Display chat rules
- `/clearrules` - Clear chat rules
- Support for text, photo, video, document, sticker, voice, animation notes
- Reply-to-message note saving

### 📊 Report System
- `/report [reason]` - Report messages/users (reply to message)
- `/reports on|off` - Toggle report system
- `/reports adminonly on|off` - Admin-only report visibility
- `/reports cooldown <seconds>` - Set report cooldown
- `/reporthistory` - View report history
- Interactive report handling with action buttons
- Automatic admin notification system
- Report status tracking (pending/resolved/dismissed)
- Private confirmation to reporters

### 🎛️ Advanced Chat Features
- `/setlang <language>` - Set chat language (en/es/fr/de/it/pt/ru/ar/hi/zh)
- `/nightmode on|off` - Toggle night mode restrictions
- `/nightmode set 22:00 06:00` - Set night mode hours
- `/nightmode status` - Show night mode settings
- `/slowmode <seconds>` - Set slow mode delay
- `/slowmode on|off` - Toggle slow mode
- `/slowmode status` - Show slow mode settings
- Automatic night mode enforcement
- Timezone support for night mode

### 🔧 Custom Commands System
- `/addcmd <command> <response>` - Add custom commands
- `/delcmd <command>` - Delete custom commands
- `/listcmds` - List all custom commands
- Dynamic command execution
- Admin-only command creation

### 🧹 Maintenance & Utilities
- `/cleanup <days>` - Remove users inactive for X days
- `/backup` - Backup chat settings and data
- Automatic database cleanup routines
- Settings import/export preparation

### 🔒 Admin Verification System (UNIQUE)
- `/verify` - Learn about admin verification
- **Forward message verification** - Forward any message to bot in private
- Cross-chat admin status checking
- Scammer protection warnings
- Detailed verification reports

### 🛑 Owner Service Controls (super admin only)
- `/disable` / `/disableservices` `[chat_id]` - Owner disables ALL bot services in a group
- `/resume` / `/resumeservices` `[chat_id]` - Owner resumes all services (group admins **cannot**)
- `/disabledgroups` - List all groups whose services are currently disabled
- Persisted in the `disabled_chats` table on SQLite / PostgreSQL / MySQL
- Enforced across messages, joins/leaves, captchas, filters, notes, custom commands, reports, and moderation commands

### ❓ Help & Information
- `/help` - Complete command reference
- `/start` - Welcome message and setup guide
- `/about` - Bot information and features
- `/commands` - Quick command reference

### 🔗 Invite Links & Join Statistics
- `/link` - Create a unique invite link for each user (joins tracked per link)
- `/link_stat` / `/linkstats` - Show total joins per invite link (admins see all)
- Join attribution via Telegram's invite-link "name" field
- Per-user link reuse (each member keeps one link)

### ⚙️ User Commands (admins configure, members use)
- `/usercmd add <name> <response>` - Create a member-usable `!name` command
- `/usercmd del <name>` - Delete a member command
- `/usercmd on|off <name>` - Enable/disable a member command
- `/usercmd setup <name> <response>` - Update a member command's response
- `/usercmd list` - List all member commands
- Members invoke them with `!name` in the group

### 📊 Chat Statistics & Leaderboards
- `/stats` / `/statistics` - Total active members, admins, bans, warnings, mutes, whitelist
- `/top` / `/leaderboard` - Top active members by message count
- Persistent message-count tracking (survives bot restarts)
- Per-chat aggregation with username resolution

### 🌐 Web Dashboard (Optional)
- Real-time statistics dashboard
- Chat and user management interface
- Report monitoring
- Activity logs and analytics
- Health monitoring endpoints
- API endpoints for external integration

## 🎯 Unique Features Not Found in Other Bots

1. **Admin Verification System** - Forward message verification to prevent scammer impersonation
2. **Comprehensive Web Dashboard** - Real-time monitoring and management
3. **Advanced Report System** - Interactive report handling with action buttons
4. **Global Cross-Chat Protection** - Unified ban/whitelist across all bot chats
5. **Flexible Time Parsing** - Natural language time input (30s, 5m, 2h, 1d)
6. **Multi-Database Support** - SQLite, PostgreSQL, MySQL compatibility
7. **Complete Open Source** - Full source code available for customization
8. **Modular Architecture** - Easy to extend and customize
9. **Advanced Logging** - Comprehensive audit trail and debugging
10. **Production Ready** - Full deployment guides and monitoring

## 📊 Feature Comparison

| Feature | Our Bot | Miss Rose | Combot | Group Help | Safeguard |
|---------|---------|-----------|--------|------------|-----------|
| Basic Moderation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Flood Protection | ✅ | ✅ | ✅ | ✅ | ✅ |
| Word Filters | ✅ | ✅ | ✅ | ✅ | ✅ |
| Welcome System | ✅ | ✅ | ✅ | ✅ | ❌ |
| Captcha System | ✅ | ✅ | ❌ | ✅ | ✅ |
| Notes System | ✅ | ✅ | ✅ | ✅ | ❌ |
| Report System | ✅ | ✅ | ✅ | ✅ | ❌ |
| Night Mode | ✅ | ✅ | ❌ | ✅ | ❌ |
| Custom Commands | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Admin Verification** | ✅ | ❌ | ❌ | ❌ | ❌ |
| Global Systems | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Web Dashboard** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Open Source** | ✅ | ❌ | ❌ | ❌ | ❌ |

## 🛠️ Technical Features

### Database & Storage
- SQLAlchemy ORM with multiple database support
- SQLite (default), PostgreSQL, MySQL compatibility
- Automatic database migrations
- Comprehensive data models for all features
- Efficient indexing and query optimization

### Security & Protection
- Admin-only command protection
- Global ban enforcement across chats
- Silent moderation options
- Comprehensive audit logging
- Rate limiting and cooldown systems
- Input validation and sanitization

### Performance & Scalability
- Async/await implementation
- Efficient message processing pipeline
- Memory-optimized flood tracking
- Connection pooling support
- Horizontal scaling preparation

### Error Handling & Logging
- Comprehensive error handling
- User-friendly error messages
- Detailed logging for debugging
- Graceful degradation on failures
- Automatic recovery mechanisms

## 📦 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot))

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/meghlabd275-byte/Tgbot.git
   cd Telegram-Bot-
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file:
   ```env
   BOT_TOKEN=your_bot_token_here
   BOT_USERNAME=your_bot_username_here
   SUPER_ADMIN_ID=your_telegram_user_id_here
   DATABASE_URL=sqlite:///bot.db
   LOG_LEVEL=INFO
   ```

4. **Test the Setup**
   ```bash
   python test_bot.py
   ```

5. **Run the Bot**
   ```bash
   python bot.py
   ```

6. **Optional: Start Web Dashboard**
   ```bash
   python web_dashboard.py
   ```
   Access at: http://localhost:5000

### Adding to Groups

1. **Start the bot first** — run `python bot.py` (or deploy it). The bot must be
   online before you add it to a group.

2. **Add the bot to your group**:
   - Open the group → tap the group name → **Administrators** → **Add Admin** →
     search for your bot's username and add it.
   - Or open a chat with the bot and tap **⋯ → Add to Group / Channel**.

3. **Grant the necessary admin permissions**:
   - *Change group info* (welcome/captcha/title changes)
   - *Delete messages* (purge/delete/filters/URL removal)
   - *Ban users* (ban/kick/mute)
   - *Invite users via link* (`/link` and captcha)

4. **Activate the group** — send `/activate` in the group (as an admin). This
   registers the chat and auto-syncs the group's admins into the bot's cache.

5. **Verify it works** — send `/help` to list every command, `/stats` to view
   activity, and `/link` to generate your own invite link.

> **Tip:** the bot auto-registers any group admin who runs an admin command, so
> moderation works immediately. Only the bot owner (`SUPER_ADMIN_ID`) can use
> `/disable` / `/resume` to turn all services on or off for a group.

## 🚀 Deployment Options

### Local Development
Perfect for testing and small groups:
```bash
python bot.py
```

### VPS/Server Deployment
For production use with systemd:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### Docker Deployment
Using Docker Compose:
```bash
docker-compose up -d
```

### Cloud Platforms
- **Heroku** - One-click deployment
- **Railway** - GitHub integration
- **DigitalOcean** - App Platform
- **AWS/GCP/Azure** - Full cloud deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guides.

## 📚 Documentation

- **[API Reference](API_REFERENCE.md)** - Complete command and API documentation
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment strategies
- **[Feature List](FEATURE_LIST.md)** - Comprehensive feature comparison
- **[Changelog](CHANGELOG.md)** - Version history and updates

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/meghlabd275-byte/Tgbot/issues)
- **Documentation**: [Complete Docs](README.md)
- **Examples**: Check the `examples/` directory

## 🌟 Star History

If you find this bot useful, please consider giving it a star! ⭐

## 📈 Statistics

- **Total Commands**: 80+ commands
- **Handler Modules**: 10 specialized modules
- **Database Tables**: 15+ comprehensive tables
- **Lines of Code**: 4000+ lines
- **Features**: 100+ individual features
- **Documentation**: Complete guides and references

---

**Made with ❤️ for the Telegram community**

*This bot combines the best features from all popular Telegram admin bots while adding unique capabilities not found elsewhere!*