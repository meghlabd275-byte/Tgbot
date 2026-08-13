from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command, parse_time_string, format_time_duration
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# In-memory flood tracking
flood_tracker = defaultdict(lambda: deque())
flood_settings = {}

class FloodControl:
    def __init__(self):
        self.user_messages = defaultdict(lambda: deque())
        self.flood_settings = {}
    
    def add_message(self, chat_id: int, user_id: int):
        """Add a message to flood tracking"""
        now = datetime.now()
        
        # Get flood settings for chat
        settings = self.get_flood_settings(chat_id)
        if not settings['enabled']:
            return False
        
        # Clean old messages
        cutoff = now - timedelta(seconds=settings['time_window'])
        user_key = f"{chat_id}:{user_id}"
        
        # Remove old messages
        while self.user_messages[user_key] and self.user_messages[user_key][0] < cutoff:
            self.user_messages[user_key].popleft()
        
        # Add current message
        self.user_messages[user_key].append(now)
        
        # Check if flood limit exceeded
        if len(self.user_messages[user_key]) > settings['limit']:
            return True
        
        return False
    
    def get_flood_settings(self, chat_id: int):
        """Get flood settings for a chat"""
        if chat_id not in self.flood_settings:
            self.flood_settings[chat_id] = {
                'enabled': False,
                'limit': 5,
                'time_window': 10,  # seconds
                'action': 'mute',  # mute, kick, ban
                'duration': 3600   # mute duration in seconds
            }
        return self.flood_settings[chat_id]
    
    def set_flood_settings(self, chat_id: int, **kwargs):
        """Update flood settings for a chat"""
        settings = self.get_flood_settings(chat_id)
        settings.update(kwargs)
        self.flood_settings[chat_id] = settings

# Global flood control instance
flood_control = FloodControl()

@is_admin_command
@is_group_command
async def setflood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set flood protection limit"""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ Please provide a valid number.\n"
            "Usage: `/setflood 5` (allow 5 messages per 10 seconds)\n"
            "Use `/setflood 0` to disable flood protection.",
            parse_mode='Markdown'
        )
        return
    
    limit = int(context.args[0])
    chat_id = update.effective_chat.id
    
    if limit == 0:
        flood_control.set_flood_settings(chat_id, enabled=False)
        await update.message.reply_text("✅ Flood protection has been disabled.")
    else:
        flood_control.set_flood_settings(chat_id, enabled=True, limit=limit)
        settings = flood_control.get_flood_settings(chat_id)
        await update.message.reply_text(
            f"✅ Flood protection set to {limit} messages per {settings['time_window']} seconds.\n"
            f"Action: {settings['action'].title()}"
        )

@is_admin_command
@is_group_command
async def setfloodmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set flood protection action"""
    if not context.args or context.args[0].lower() not in ['mute', 'kick', 'ban']:
        await update.message.reply_text(
            "❌ Please specify a valid action.\n"
            "Usage: `/setfloodmode mute|kick|ban`\n"
            "Available actions:\n"
            "• `mute` - Mute the user temporarily\n"
            "• `kick` - Kick the user from group\n"
            "• `ban` - Ban the user permanently",
            parse_mode='Markdown'
        )
        return
    
    action = context.args[0].lower()
    duration = 3600  # Default 1 hour for mute
    
    if action == 'mute' and len(context.args) > 1:
        duration = parse_time_string(context.args[1])
    
    chat_id = update.effective_chat.id
    flood_control.set_flood_settings(chat_id, action=action, duration=duration)
    
    if action == 'mute':
        await update.message.reply_text(
            f"✅ Flood action set to **{action}** for {format_time_duration(duration)}.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"✅ Flood action set to **{action}**.",
            parse_mode='Markdown'
        )

@is_admin_command
@is_group_command
async def flood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current flood settings"""
    chat_id = update.effective_chat.id
    settings = flood_control.get_flood_settings(chat_id)
    
    if not settings['enabled']:
        await update.message.reply_text("🌊 Flood protection is currently **disabled**.", parse_mode='Markdown')
        return
    
    flood_info = f"""🌊 **Flood Protection Settings**

**Status:** Enabled
**Limit:** {settings['limit']} messages per {settings['time_window']} seconds
**Action:** {settings['action'].title()}"""
    
    if settings['action'] == 'mute':
        flood_info += f"\n**Mute Duration:** {format_time_duration(settings['duration'])}"
    
    flood_info += f"""

**How it works:**
If a user sends more than {settings['limit']} messages in {settings['time_window']} seconds, they will be {settings['action']}d automatically.

**Commands:**
• `/setflood <number>` - Set message limit
• `/setfloodmode <action>` - Set action (mute/kick/ban)
• `/flood` - Show current settings"""
    
    await update.message.reply_text(flood_info, parse_mode='Markdown')

async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is flooding and take action"""
    if not update.message or not update.effective_user:
        return False
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Skip admins and whitelisted users
    if db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id):
        return False
    
    # Check for flood
    if flood_control.add_message(chat_id, user_id):
        settings = flood_control.get_flood_settings(chat_id)
        
        try:
            if settings['action'] == 'mute':
                until_date = datetime.now() + timedelta(seconds=settings['duration'])
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=context.bot.get_chat(chat_id).permissions,
                    until_date=until_date
                )
                db.add_mute(user_id, chat_id, context.bot.id, settings['duration'], "Flood protection")
                
                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been muted for {format_time_duration(settings['duration'])} due to flooding!"
                )
                
            elif settings['action'] == 'kick':
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                
                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been kicked due to flooding!"
                )
                
            elif settings['action'] == 'ban':
                await context.bot.ban_chat_member(chat_id, user_id)
                db.add_ban(user_id, chat_id, context.bot.id, "Flood protection")
                
                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been banned due to flooding!"
                )
            
            # Delete the action message after 5 seconds
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat_id, action_msg.message_id),
                5
            )
            
            logger.info(f"Flood protection: {settings['action']}ed user {user_id} in chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying flood protection: {e}")
    
    return False