import re
from typing import Optional, Union
from telegram import Update, User
from telegram.ext import ContextTypes

def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[tuple]:
    """
    Extract user information from command arguments or replied message.
    Returns tuple of (user_id, user_object) or None if no user found.
    """
    message = update.effective_message
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user
    
    # Check command arguments
    if context.args:
        arg = context.args[0]
        
        # Check if it's a user ID (numeric)
        if arg.isdigit():
            user_id = int(arg)
            return user_id, None
        
        # Check if it's a username (starts with @)
        if arg.startswith('@'):
            username = arg[1:]  # Remove @
            # Try to get user from chat members (limited functionality)
            return None, username
    
    return None

def format_user_mention(user: User) -> str:
    """Format user mention for display"""
    if user.username:
        return f"@{user.username}"
    else:
        name = user.first_name
        if user.last_name:
            name += f" {user.last_name}"
        return f"[{name}](tg://user?id={user.id})"

def parse_time_string(time_str: str) -> int:
    """
    Parse time string like '1h', '30m', '2d' into seconds.
    Returns seconds or default 3600 (1 hour) if parsing fails.
    """
    if not time_str:
        return 3600
    
    time_str = time_str.lower().strip()
    
    # Extract number and unit
    match = re.match(r'^(\d+)([smhd]?)$', time_str)
    if not match:
        return 3600
    
    number = int(match.group(1))
    unit = match.group(2) or 's'
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    return number * multipliers.get(unit, 1)

def format_time_duration(seconds: int) -> str:
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"

def is_admin_command(func):
    """Decorator to check if user is admin before executing command"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from database import db
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not db.is_admin(user_id, chat_id):
            await update.message.reply_text("❌ You need to be an admin to use this command.")
            return
        
        return await func(update, context)
    
    return wrapper

def is_group_command(func):
    """Decorator to ensure command is used in a group"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ This command can only be used in groups.")
            return
        
        return await func(update, context)
    
    return wrapper

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_chat_admins_cache():
    """Simple in-memory cache for chat admins"""
    if not hasattr(get_chat_admins_cache, 'cache'):
        get_chat_admins_cache.cache = {}
    return get_chat_admins_cache.cache

async def update_chat_admins_cache(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Update the chat admins cache"""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        cache = get_chat_admins_cache()
        cache[chat_id] = [admin.user.id for admin in admins]
        return True
    except Exception:
        return False

def get_file_id_from_message(message) -> Optional[str]:
    """Extract file ID from various message types"""
    if message.photo:
        return message.photo[-1].file_id  # Get highest resolution
    elif message.document:
        return message.document.file_id
    elif message.video:
        return message.video.file_id
    elif message.audio:
        return message.audio.file_id
    elif message.voice:
        return message.voice.file_id
    elif message.video_note:
        return message.video_note.file_id
    elif message.sticker:
        return message.sticker.file_id
    elif message.animation:
        return message.animation.file_id
    
    return None