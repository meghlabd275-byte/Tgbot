import re
import functools
from typing import Optional
from telegram import Update, User
from telegram.ext import ContextTypes

# ---------------------------------------------------------------------------
# Time parsing (supports natural language like "30s", "5m", "2h", "1d")
# ---------------------------------------------------------------------------

_TIME_MULTIPLIERS = {
    's': 1,
    'sec': 1,
    'secs': 1,
    'second': 1,
    'seconds': 1,
    'm': 60,
    'min': 60,
    'mins': 60,
    'minute': 60,
    'minutes': 60,
    'h': 3600,
    'hr': 3600,
    'hrs': 3600,
    'hour': 3600,
    'hours': 3600,
    'd': 86400,
    'day': 86400,
    'days': 86400,
    'w': 604800,
    'week': 604800,
    'weeks': 604800,
}

_TIME_PATTERN = re.compile(r'^\s*(\d+)\s*([a-zA-Z]*)\s*$')


def parse_time_string(time_str) -> int:
    """
    Parse a time string like '1h', '30m', '2 days', '1w' into seconds.
    Also accepts plain integers (interpreted as minutes). Returns the
    default (3600s) if parsing fails.
    """
    if time_str is None:
        return 3600

    if isinstance(time_str, int) or (isinstance(time_str, str) and time_str.strip().isdigit()):
        # Bare number -> minutes (common convention for /mute 5 = 5 minutes)
        return int(time_str) * 60

    text = str(time_str).lower().strip()
    match = _TIME_PATTERN.match(text)
    if not match:
        return 3600

    number = int(match.group(1))
    unit = (match.group(2) or 'm').lower()
    multiplier = _TIME_MULTIPLIERS.get(unit, 60)
    return number * multiplier


def format_time_duration(seconds: int) -> str:
    """Format seconds into a human readable duration (e.g. '2h 30m')."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    parts = []
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts)


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
        
        # Resolve a bare @username against the bot's local user directory.
        # Telegram's Bot API offers no username->id lookup for private users,
        # so we fall back to the users we have previously seen in any chat.
        if arg.startswith('@'):
            username = arg.lstrip('@').lower()
            try:
                from database import db
                session = db.get_session()
                try:
                    row = session.query(db.User).filter(
                        db.User.username.ilike(username)
                    ).first()
                    if row is not None:
                        return row.id, row
                finally:
                    session.close()
            except Exception:
                pass
            return None
    
    return None

def format_user_mention(user: User) -> str:
    """Format user mention for display"""
    if user is None:
        return "Unknown user"
    if user.username:
        return f"@{user.username}"
    else:
        name = user.first_name
        if user.last_name:
            name += f" {user.last_name}"
        return f"[{name}](tg://user?id={user.id})"

def is_admin_command(func):
    """Decorator to check if user is admin before executing command"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from database import db
        from config import Config

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Resolve the target chat for private-chat connections: an admin who
        # connected their PM to a group can run admin commands from there.
        try:
            from handlers.connections import get_effective_chat_id
            chat_id = get_effective_chat_id(update, context)
        except Exception:
            chat_id = update.effective_chat.id

        # Owner kill-switch: if this group's services are disabled, block every
        # admin command for group admins. Only the bot owner (super admin) can
        # still act (e.g. /resume from inside the disabled group).
        if db.is_chat_disabled(chat_id) and user_id not in Config.super_admin_ids():
            await update.message.reply_text(
                "🛑 This group's bot services are disabled by the bot owner. "
                "Only the owner can resume them."
            )
            return None

        # Fall back to Telegram's own admin list when the bot's admin
        # database is empty (e.g. bot was just added to a new group).
        if not db.is_admin(user_id, chat_id):
            telegram_admin = await is_telegram_admin(context, chat_id, user_id)
            if telegram_admin:
                # Auto-register so future checks hit the local cache.
                db.get_or_create_chat(chat_id, update.effective_chat.title)
                db.add_admin(user_id, chat_id)
            else:
                await update.message.reply_text("❌ You need to be an admin to use this command.")
                return None

        return await func(update, context)

    return wrapper

def is_group_command(func):
    """Decorator to ensure command is used in a group (or via a private-chat
    connection to a group)."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == 'private':
            try:
                from handlers.connections import get_connection
                if not get_connection(update.effective_user.id):
                    await update.message.reply_text(
                        "❌ This command can only be used in groups.\n"
                        "Connect to a group first with `/connect <chat>`."
                    )
                    return
            except Exception:
                await update.message.reply_text("❌ This command can only be used in groups.")
                return

        return await func(update, context)

    return wrapper

def is_super_admin_command(func):
    """Decorator: only the bot owner (super admin) can run this command.

    This is intentionally stricter than `is_admin_command`: group admins canNOT
    use owner-only commands (e.g. disabling/resuming a group's services).
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config

        user_id = update.effective_user.id
        if user_id in Config.super_admin_ids():
            return await func(update, context)

        await update.message.reply_text(
            "❌ This command is reserved for the bot owner (super admin)."
        )
        return None

    return wrapper

def is_owner_command(func):
    """Decorator: only the group creator/owner (or a super admin) can run it."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config
        from database import db

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if user_id in Config.super_admin_ids():
            return await func(update, context)

        try:
            if await is_telegram_owner(context, chat_id, user_id):
                return await func(update, context)
        except Exception:
            pass

        await update.message.reply_text("❌ Only the group owner can use this command.")
        return

    return wrapper

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

async def is_telegram_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Ask Telegram directly whether `user_id` is an admin/owner of `chat_id`."""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return str(member.status) in ('administrator', 'creator')
    except Exception:
        return False

async def get_telegram_admins(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Return the list of Telegram admin users for a chat."""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return [a.user for a in admins]
    except Exception:
        return None

async def is_telegram_owner(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Ask Telegram directly whether `user_id` is the group creator/owner."""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return str(member.status) == 'creator'
    except Exception:
        return False

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

async def sync_telegram_admins(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    Register all current Telegram admins/owner of a chat in the bot's local
    admin database. This ensures "the admin who added the bot can set it up"
    and every other admin of that group works in any group the bot is in.
    """
    from database import db
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        db.get_or_create_chat(chat_id)
        for admin in admins:
            user = admin.user
            db.add_admin(user.id, chat_id, admin.custom_title or None)
            db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
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