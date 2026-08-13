# 🤖 Advanced Telegram Admin Bot Features

This document describes all the advanced features that have been added to make this bot comprehensive and competitive with popular Telegram admin bots like Miss Rose, Combot, Group Help, Safeguard, and URL remove bot.

## 📋 Table of Contents

1. [Anti-Flood Protection](#anti-flood-protection)
2. [Message Filtering System](#message-filtering-system)
3. [Welcome & Goodbye System](#welcome--goodbye-system)
4. [Notes & Rules System](#notes--rules-system)
5. [Report System](#report-system)
6. [Advanced Features](#advanced-features)
7. [Database Schema](#database-schema)
8. [Command Reference](#command-reference)

---

## 🌊 Anti-Flood Protection

Prevents users from spamming messages in your group.

### Commands:
- `/setflood <number>` - Set flood limit (max messages per minute)
- `/setfloodmode <action>` - Set action for flood violations (ban/kick/mute/warn)
- `/flood` - View current flood settings

### Features:
- Configurable message limits per minute
- Multiple action types: ban, kick, mute, warn
- Automatic cleanup of flood messages
- Admin exemption
- Per-chat configuration

---

## 🔍 Message Filtering System

Advanced filtering system for words, URLs, media, and spam detection.

### Word Filters:
- `/addfilter <word> [action]` - Add word filter with optional action
- `/removefilter <word>` - Remove word filter
- `/filters` - List all active filters

### Content Locks:
- `/lock <type>` - Lock specific content types
- `/unlock <type>` - Unlock content types
- `/locks` - View current lock settings

**Lockable content types:**
- `text` - Text messages
- `media` - Photos, videos, documents
- `stickers` - Sticker messages
- `gif` - GIF animations
- `url` - URLs and links
- `button` - Inline keyboard buttons
- `forward` - Forwarded messages
- `game` - Game messages
- `location` - Location sharing
- `rtl` - Right-to-left text
- `tglink` - Telegram invite links
- `all` - All message types

### Anti-Spam:
- `/antispam <on/off>` - Toggle automatic spam detection
- Detects common spam patterns
- Automatic action on spam detection

### Actions Available:
- `delete` - Delete the message
- `warn` - Warn the user
- `mute` - Mute the user
- `kick` - Kick the user
- `ban` - Ban the user

---

## 👋 Welcome & Goodbye System

Customizable welcome and goodbye messages with captcha support.

### Commands:
- `/setwelcome <message>` - Set welcome message
- `/setgoodbye <message>` - Set goodbye message
- `/welcome` - View current welcome settings
- `/goodbye` - View current goodbye settings
- `/captcha <on/off>` - Toggle captcha for new members
- `/cleanservice <on/off>` - Auto-delete service messages

### Message Variables:
- `{first}` - User's first name
- `{last}` - User's last name
- `{fullname}` - User's full name
- `{username}` - User's username
- `{mention}` - Mention the user
- `{id}` - User's ID
- `{chatname}` - Chat name
- `{count}` - Member count

### Captcha Features:
- Math captcha for new members
- Automatic kick if failed
- Configurable timeout
- Button-based verification

---

## 📝 Notes & Rules System

Save and retrieve information easily.

### Notes:
- `/save <notename> <content>` - Save a note
- `/get <notename>` - Retrieve a note
- `#<notename>` - Quick note retrieval
- `/clear <notename>` - Delete a note
- `/notes` - List all notes

### Rules:
- `/setrules <rules>` - Set chat rules
- `/rules` - View chat rules
- `/clearrules` - Clear chat rules

### Note Features:
- Support for text, media, and buttons
- Private notes (only admins can retrieve)
- Note shortcuts with # prefix
- Rich formatting support

---

## 📢 Report System

Allow users to report issues to admins.

### Commands:
- `/report` - Report a message (reply to message)
- `/reports <on/off>` - Toggle report system
- `/reporthistory` - View report history (admin only)

### Features:
- Anonymous reporting
- Admin notification system
- Report cooldown to prevent spam
- Report history tracking
- Quick admin actions on reports

---

## ⚡ Advanced Features

Additional powerful features for enhanced group management.

### Language Settings:
- `/setlang <code>` - Set bot language (en, es, fr, de, it, pt, ru, ar, hi, zh)

### Night Mode:
- `/nightmode <on/off> [start_hour] [end_hour]` - Restrict activity during night hours

### Slow Mode:
- `/slowmode <seconds>` - Set message cooldown for users

### Custom Commands:
- `/addcmd <command> <response>` - Add custom command
- `/delcmd <command>` - Delete custom command
- `/listcmds` - List custom commands

### Cleanup Tools:
- `/cleanup` - Remove deleted accounts from chat
- `/backup` - Create chat backup (admin data)

### Federation System:
- Cross-chat ban management
- Shared ban lists
- Federation administration

---

## 🗄️ Database Schema

The bot uses the following new database tables:

### Core Tables:
- `word_filters` - Word filtering rules
- `url_filters` - URL filtering rules  
- `media_filters` - Media filtering rules
- `welcome_settings` - Welcome/goodbye configuration
- `pending_users` - Captcha verification queue
- `notes` - Saved notes and content
- `rules` - Chat rules storage
- `reports` - Report history
- `report_settings` - Report configuration
- `chat_settings` - Advanced chat settings
- `federations` - Federation management
- `custom_commands` - Custom command responses

---

## 📚 Command Reference

### Admin Commands (50+ new commands):

#### Anti-Flood:
- `/setflood <number>` - Set flood limit
- `/setfloodmode <action>` - Set flood action
- `/flood` - View flood settings

#### Filters:
- `/addfilter <word> [action]` - Add word filter
- `/removefilter <word>` - Remove word filter
- `/filters` - List filters
- `/lock <type>` - Lock content type
- `/unlock <type>` - Unlock content type
- `/locks` - View locks
- `/antispam <on/off>` - Toggle spam detection

#### Welcome System:
- `/setwelcome <message>` - Set welcome message
- `/setgoodbye <message>` - Set goodbye message
- `/welcome` - View welcome settings
- `/goodbye` - View goodbye settings
- `/captcha <on/off>` - Toggle captcha
- `/cleanservice <on/off>` - Auto-delete service messages

#### Notes & Rules:
- `/save <name> <content>` - Save note
- `/get <name>` - Get note
- `/clear <name>` - Delete note
- `/notes` - List notes
- `/setrules <rules>` - Set rules
- `/rules` - View rules
- `/clearrules` - Clear rules

#### Reports:
- `/report` - Report message
- `/reports <on/off>` - Toggle reports
- `/reporthistory` - View report history

#### Advanced:
- `/setlang <code>` - Set language
- `/nightmode <on/off>` - Toggle night mode
- `/slowmode <seconds>` - Set slow mode
- `/addcmd <cmd> <response>` - Add custom command
- `/delcmd <cmd>` - Delete custom command
- `/listcmds` - List custom commands
- `/cleanup` - Remove deleted accounts
- `/backup` - Create backup

### User Commands:
- `/report` - Report a message
- `/rules` - View chat rules
- `#<notename>` - Get note quickly
- Custom commands (as defined by admins)

---

## 🔧 Configuration

All features are configurable per chat and respect the existing admin system. The bot maintains backward compatibility with all existing commands while adding comprehensive new functionality.

### Key Features:
- ✅ **50+ new commands** for comprehensive group management
- ✅ **Advanced filtering** with multiple content types and actions
- ✅ **Smart anti-spam** with pattern detection
- ✅ **Captcha system** for new member verification
- ✅ **Report system** with admin notifications
- ✅ **Custom commands** for personalized responses
- ✅ **Night mode** for time-based restrictions
- ✅ **Federation support** for cross-chat management
- ✅ **Backup system** for data protection
- ✅ **Multi-language support** for international groups

This makes the bot competitive with and often superior to popular alternatives like Miss Rose, Combot, and other admin bots.