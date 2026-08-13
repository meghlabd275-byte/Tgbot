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