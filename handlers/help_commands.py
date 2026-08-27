from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message with all available commands"""
    help_text = """
🤖 **Telegram Admin Bot - Command List**

**[Admin] Utility Commands**
/fileid - Reply to a message to get the File ID of a media message

**[Admin] Chat Management**
/activate - Register the current chat
/silence - Only allow admins to chat
/unsilence - Allow all users to chat
/ua, /underattack - Toggle under attack mode on/off
/reload - Reload the list of admins saved in the bot cache
/debug - Print out debug information for your chat and bot settings
/pin - Pin a chat message (reply to message)
/unpin - Un-pin the last pinned message
/purge [amount] - Delete messages (reply to start point or specify amount)
/spurge [amount] - Silently purge messages (no confirmation)
/del, /delete - Delete the replied-to message
/adminlist, /admins - List the group's admins
/warnmode [mode] - Set warning-limit action (kick/ban/mute/tban)

**[Admin] User Management**
/promote - Add a user as an admin *
/title - Add a title to a user *
/demote - Remove a user from admin *

/ban - Remove a user from the chat (cannot return) *
/sban - Silently remove a user from the chat *
/gban - Globally remove a user from all bot chats *
/sgban - Silently & globally remove a user *

/unban - Remove a ban from a particular user *
/gunban - Globally remove a user ban from all bot chats *
/banlist - View a list of banned users

/kick - Kick a user from the chat (can return) *
/skick - Silently kick a user from the chat *
/gkick - Globally kick a user from all chats *

/mute [time] - Mute a user for a period of time *
/unmute - Allow a user to chat after being muted *
/smute [time] - Silently mute a user *

/warn - Issue a warning to a user *
/gwarn - Globally issue a warning to a user *
/swarn - Silently warn a user *
/unwarn - Remove a warning from the user *
/resetwarns - Completely wipe any warnings a user has *
/warnings - Check warning count for a user *

/whitelist - Whitelist user so they bypass filters *
/gwhitelist - Globally whitelist a user *
/unwhitelist - Remove a user from the whitelist *
/whitelisted - View a list of whitelisted users

**[Admin] Approvals & Ignores**
/approve - Approve a user (immune to automated actions)
/unapprove - Remove approval
/approved - View approved users
/unapproveall - Remove all approvals
/ignore - Ignore a user's commands
/unignore - Remove ignore
/ignored - View ignored users

/resetuser - Remove bans, warns, mutes for a user *
/resetrep - Reset a user's reputation to 0 *
/user - View information about a user
/lastactive - View the last active date of a user *

**General Commands**
/help - Show this help message
/start - Start the bot
/id - Get user or chat ID
/chatinfo - Get information about the current chat
/verify - Learn about admin verification

**[Admin] Welcome & Goodbye**
/setwelcome <msg> - Set welcome message (vars: {first} {username} {mention} {chatname} {count})
/setgoodbye <msg> - Set goodbye message
/welcome on|off - Toggle welcome messages
/goodbye on|off - Toggle goodbye messages
/captcha on|off - Require new members to solve a captcha

**[Admin] Join Hider (hide system messages)**
/cleanservice on|off - Delete all join/leave service messages
/joinhider - Show join-hider settings
/joinhider joined on|off - Hide "X joined" messages
/joinhider left on|off - Hide "X left" messages
/joinhider all on|off - Hide both joined + left messages
/joinhider system on|off - Hide ALL service messages (pins, title/photo changes)

**[Admin] Filters & Anti-Spam**
/addfilter <word> <action> - Add a word filter (actions: delete, warn, mute, kick, ban)
/removefilter <word> - Remove a word filter
/filters - List word filters
/lock <type> - Lock a message type (url, photo, video, document, sticker, voice, etc.)
/unlock <type> - Unlock a message type
/locks - Show locked message types
/locktypes - List all lockable message types
/allowlist [domain] - Allow a domain to bypass URL locks/removal
/unallowlist <domain> - Remove a domain from the allowlist
/antispam on|off - Toggle spam-pattern detection

**[Admin] URL Remover (auto-delete links)**
/removeurls on - Auto-delete messages containing web URLs (admins exempt)
/removeurls off - Disable URL removal
/removeurls invites on|off - Also remove Telegram t.me invite links
/removeurls all on|off - Remove all link types (urls + invites + @links)
/removeurls warn on|off - Also warn the sender
/removeurls status - Show URL-remover settings

**[Admin] Anti-Flood & Anti-Raid**
/setflood <limit> - Set flood message limit (e.g. /setflood 10)
/setfloodmode <mode> - Set flood action (ban, mute, kick)
/flood - Show flood settings
/antiraid - Configure anti-raid (auto under-attack on mass joins)

**[Admin] Notes & Rules**
/save <name> <content> - Save a note (use #name to retrieve)
/get <name> - Retrieve a note
/clear <name> - Delete a note
/notes - List all notes
/setrules <text> - Set group rules
/rules - View group rules
/clearrules - Clear group rules

**[Admin] Reports & Advanced**
/report - Report a message (reply to it)
/reports - View report settings
/reporthistory - View report history
/nightmode on|off - Toggle night mode
/slowmode <seconds> - Set slow mode
/addcmd <name> <response> - Add a custom command
/delcmd <name> - Delete a custom command
/listcmds - List custom commands
/cleanup - Clean up old data
/backup - Backup bot data

**[Admin] Federations**
/fednew, /newfed <name> - Create a new federation
/feddel, /delfed - Delete your federation
/fedrename, /renamefed <name> - Rename your federation
/fedinfo - Show your federation info
/fedadmins - List federation admins
/fedpromote, /fpromote - Promote a federation admin
/feddemote, /fdemote - Demote a federation admin
/fedjoin, /joinfed <fed_id> - Join a federation
/fedleave, /leavefed - Leave the federation
/fedchat, /chatfed - Show the chat's federation
/fban, /fedban - Federation-ban a user
/fedunban, /unfban, /funban - Federation-unban a user
/fedkick, /fkick - Federation-kick a user
/fedmute, /fmute - Federation-mute a user
/fedbans, /fbans - List federation bans

**[Admin] Connections**
/connect <chat> - Connect to another chat (PM or group)
/disconnect - Disconnect
/connection, /connections - Show current connection
/reconnect - Re-connect to the last chat

**[Owner] Service Controls (super admin only)**
/disable, /disableservices [chat_id] - Disable ALL bot services in this (or the given) group
/resume, /resumeservices [chat_id] - Resume ALL bot services (owner only — group admins cannot)
/disabledgroups - List all groups whose services are currently disabled

**Admin Verification**
Forward any message from a user to the bot in private to verify if they are an admin in any chat where the bot is present.

**Command Usage Notes:**
Commands marked with * can be used in these ways:
1. /command @username
2. /command User_ID
3. Reply to a user message (no username/ID needed)

**Time Format Examples:**
- 30s (30 seconds)
- 5m (5 minutes)  
- 2h (2 hours)
- 1d (1 day)

**Need Help?**
Contact the bot administrator or check the documentation for more details.
    """
    
    await update.message.reply_text(help_text.strip(), parse_mode='Markdown')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - welcome message"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == 'private':
        start_text = f"""
👋 **Welcome {user.first_name}!**

I'm a powerful Telegram admin bot designed to help you manage your groups effectively.

🛡️ **Key Features:**
• Complete user management (ban, kick, mute, warn)
• Advanced chat moderation tools
• Admin verification system
• Global ban/whitelist system
• Reputation tracking
• Under attack mode protection

🚀 **Getting Started:**
1. Add me to your group
2. Make me an admin with necessary permissions
3. Use `/activate` to register your chat
4. Use `/help` to see all commands

🔍 **Admin Verification:**
Forward any message from a user to me in private to verify if they're a legitimate admin. This helps prevent scammer impersonation.

📚 Use `/help` for a complete command list!
        """
    else:
        start_text = f"""
👋 **Hello {user.first_name}!**

I'm ready to help manage this group. Here's what you need to know:

🔧 **Setup Required:**
1. Make me an admin with these permissions:
   • Delete messages
   • Ban users
   • Pin messages
   • Add new admins (optional)

2. Use `/activate` to register this chat
3. Use `/help` to see all available commands

🛡️ **I can help with:**
• User moderation and management
• Chat security and anti-spam
• Admin verification
• Message management

Let's get started! Use `/help` for the full command list.
        """
    
    await update.message.reply_text(start_text.strip(), parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About command - bot information"""
    about_text = """
🤖 **Telegram Admin Bot**

**Version:** 1.0.0
**Developer:** OpenHands AI
**Purpose:** Advanced group management and moderation

**Features:**
✅ Complete user management system
✅ Advanced warning and reputation system  
✅ Global ban/whitelist capabilities
✅ Admin verification service
✅ Under attack mode protection
✅ Message purging and pinning
✅ Silent moderation actions
✅ Comprehensive logging

**Security:**
🔒 Admin verification prevents impersonation
🔒 Global systems protect across all chats
🔒 Silent actions for discrete moderation
🔒 Comprehensive audit trails

**Support:**
For issues, suggestions, or questions, contact the bot administrator.

**Privacy:**
This bot only stores necessary moderation data and respects user privacy.
    """
    
    await update.message.reply_text(about_text.strip(), parse_mode='Markdown')

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a quick command reference"""
    commands_text = """
⚡ **Quick Command Reference**

**Essential Admin Commands:**
• `/ban` - Ban user
• `/kick` - Kick user  
• `/mute` - Mute user
• `/warn` - Warn user
• `/promote` - Make admin
• `/demote` - Remove admin

**Chat Control:**
• `/silence` - Admin-only chat
• `/purge` - Delete messages
• `/pin` - Pin message
• `/ua` - Under attack mode

**User Info:**
• `/user` - User information
• `/warnings` - Check warnings
• `/banlist` - View banned users

**Quick Actions:**
• `/sban` - Silent ban
• `/skick` - Silent kick
• `/smute` - Silent mute

Use `/help` for the complete list with detailed descriptions.
    """
    
    await update.message.reply_text(commands_text.strip(), parse_mode='Markdown')