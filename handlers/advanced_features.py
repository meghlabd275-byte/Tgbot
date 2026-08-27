from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command, parse_time_string, format_time_duration
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

# Add new tables for advanced features
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base

class ChatSettings(Base):
    __tablename__ = 'chat_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    language = Column(String(10), default='en')
    timezone = Column(String(50), default='UTC')
    night_mode_enabled = Column(Boolean, default=False)
    night_mode_start = Column(String(5), default='22:00')
    night_mode_end = Column(String(5), default='06:00')
    slow_mode_enabled = Column(Boolean, default=False)
    slow_mode_delay = Column(Integer, default=30)
    auto_delete_commands = Column(Boolean, default=False)
    welcome_delay_delete = Column(Integer, default=0)
    antispam_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CustomCommand(Base):
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    command = Column(String(255))
    response = Column(Text)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

def update_advanced_database():
    from database import db as database_instance
    Base.metadata.create_all(bind=database_instance.engine)

# Night mode tracking
night_mode_restrictions = {}

# Slow-mode tracking: chat_id -> {user_id: last_message_datetime}
slow_mode_tracker = {}

@is_admin_command
@is_group_command
async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set chat language"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/setlang <language>`\n"
            "Available languages: en, es, fr, de, it, pt, ru, ar, hi, zh",
            parse_mode='Markdown'
        )
        return
    
    language = context.args[0].lower()
    valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ar', 'hi', 'zh']
    
    if language not in valid_languages:
        await update.message.reply_text(f"❌ Invalid language. Available: {', '.join(valid_languages)}")
        return
    
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        
        if settings:
            settings.language = language
            session.commit()
        else:
            settings = ChatSettings(chat_id=chat_id, language=language)
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(f"✅ Language set to {language.upper()}")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def nightmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure night mode"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• `/nightmode on` - Enable night mode\n"
            "• `/nightmode off` - Disable night mode\n"
            "• `/nightmode set 22:00 06:00` - Set night hours\n"
            "• `/nightmode status` - Show current settings",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    
    if context.args[0].lower() == 'status':
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if not settings:
                await update.message.reply_text("❌ No night mode settings found.")
                return
            
            status_text = f"""🌙 **Night Mode Settings**

**Status:** {'✅ Enabled' if settings.night_mode_enabled else '❌ Disabled'}
**Start Time:** {settings.night_mode_start}
**End Time:** {settings.night_mode_end}

**During night mode:**
• Only admins can send messages
• Media messages are restricted
• New users are auto-muted"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
        
        finally:
            session.close()
        return
    
    elif context.args[0].lower() in ['on', 'off']:
        status = context.args[0].lower() == 'on'
        
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if settings:
                settings.night_mode_enabled = status
                session.commit()
            else:
                settings = ChatSettings(chat_id=chat_id, night_mode_enabled=status)
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"🌙 Night mode {'enabled' if status else 'disabled'}.")
        
        finally:
            session.close()
    
    elif context.args[0].lower() == 'set' and len(context.args) == 3:
        start_time = context.args[1]
        end_time = context.args[2]
        
        # Validate time format
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
        if not time_pattern.match(start_time) or not time_pattern.match(end_time):
            await update.message.reply_text("❌ Invalid time format. Use HH:MM (24-hour format)")
            return
        
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if settings:
                settings.night_mode_start = start_time
                settings.night_mode_end = end_time
                session.commit()
            else:
                settings = ChatSettings(
                    chat_id=chat_id,
                    night_mode_start=start_time,
                    night_mode_end=end_time
                )
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"🌙 Night mode hours set: {start_time} - {end_time}")
        
        finally:
            session.close()

@is_admin_command
@is_group_command
async def slowmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure slow mode"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage:\n"
            "• `/slowmode on` - Enable slow mode (30s default)\n"
            "• `/slowmode off` - Disable slow mode\n"
            "• `/slowmode 60` - Set delay to 60 seconds\n"
            "• `/slowmode status` - Show current settings",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    
    if context.args[0].lower() == 'status':
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if not settings or not settings.slow_mode_enabled:
                await update.message.reply_text("🐌 Slow mode is disabled.")
                return
            
            await update.message.reply_text(
                f"🐌 **Slow Mode:** Enabled\n"
                f"**Delay:** {settings.slow_mode_delay} seconds",
                parse_mode='Markdown'
            )
        
        finally:
            session.close()
        return
    
    elif context.args[0].lower() in ['on', 'off']:
        status = context.args[0].lower() == 'on'
        
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if settings:
                settings.slow_mode_enabled = status
                session.commit()
            else:
                settings = ChatSettings(chat_id=chat_id, slow_mode_enabled=status)
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"🐌 Slow mode {'enabled' if status else 'disabled'}.")
        
        finally:
            session.close()
    
    elif context.args[0].isdigit():
        delay = int(context.args[0])
        if delay < 1 or delay > 3600:
            await update.message.reply_text("❌ Delay must be between 1 and 3600 seconds.")
            return
        
        session = db.get_session()
        try:
            settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
            
            if settings:
                settings.slow_mode_enabled = True
                settings.slow_mode_delay = delay
                session.commit()
            else:
                settings = ChatSettings(
                    chat_id=chat_id,
                    slow_mode_enabled=True,
                    slow_mode_delay=delay
                )
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"🐌 Slow mode enabled with {delay} second delay.")
        
        finally:
            session.close()

@is_admin_command
@is_group_command
async def addcmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add custom command"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/addcmd <command> <response>`\n"
            "Example: `/addcmd hello Welcome to our group!`",
            parse_mode='Markdown'
        )
        return
    
    command = context.args[0].lower()
    response = ' '.join(context.args[1:])
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    # Check if command already exists
    session = db.get_session()
    try:
        existing = session.query(CustomCommand).filter(
            CustomCommand.chat_id == chat_id,
            CustomCommand.command == command
        ).first()
        
        if existing:
            existing.response = response
            existing.created_by = admin_id
            session.commit()
            await update.message.reply_text(f"✅ Updated custom command `/{command}`")
        else:
            custom_cmd = CustomCommand(
                chat_id=chat_id,
                command=command,
                response=response,
                created_by=admin_id
            )
            session.add(custom_cmd)
            session.commit()
            await update.message.reply_text(f"✅ Added custom command `/{command}`")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def delcmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete custom command"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/delcmd <command>`")
        return
    
    command = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        custom_cmd = session.query(CustomCommand).filter(
            CustomCommand.chat_id == chat_id,
            CustomCommand.command == command
        ).first()
        
        if custom_cmd:
            session.delete(custom_cmd)
            session.commit()
            await update.message.reply_text(f"✅ Deleted custom command `/{command}`")
        else:
            await update.message.reply_text(f"❌ Custom command `/{command}` not found.")
    
    finally:
        session.close()

async def listcmds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List custom commands"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        commands = session.query(CustomCommand).filter(CustomCommand.chat_id == chat_id).all()
        
        if not commands:
            await update.message.reply_text("📝 No custom commands set for this chat.")
            return
        
        cmd_list = "📝 **Custom Commands:**\n\n"
        for cmd in commands:
            cmd_list += f"• `/{cmd.command}`\n"
        
        cmd_list += f"\n**Total:** {len(commands)} commands"
        await update.message.reply_text(cmd_list, parse_mode='Markdown')
    
    finally:
        session.close()

async def handle_custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle custom commands"""
    if not update.message or not update.message.text or not update.message.text.startswith('/'):
        return False
    
    command = update.message.text[1:].split()[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        custom_cmd = session.query(CustomCommand).filter(
            CustomCommand.chat_id == chat_id,
            CustomCommand.command == command
        ).first()
        
        if custom_cmd:
            await update.message.reply_text(custom_cmd.response, parse_mode='Markdown')
            return True
    
    finally:
        session.close()
    
    return False

@is_admin_command
@is_group_command
async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean up inactive users"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/cleanup <days>`\n"
            "This will kick users who haven't been active for the specified number of days.",
            parse_mode='Markdown'
        )
        return
    
    try:
        days = int(context.args[0])
        if days < 1 or days > 365:
            await update.message.reply_text("❌ Days must be between 1 and 365.")
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid number of days.")
        return
    
    chat_id = update.effective_chat.id
    cutoff_date = datetime.now() - timedelta(days=days)
    
    session = db.get_session()
    try:
        # Get inactive users
        inactive_users = session.query(db.User).filter(
            db.User.last_active < cutoff_date
        ).all()
        
        if not inactive_users:
            await update.message.reply_text(f"✅ No inactive users found (inactive for {days} days).")
            return
        
        # Confirm action
        await update.message.reply_text(
            f"⚠️ Found {len(inactive_users)} users inactive for {days}+ days.\n"
            f"Reply with 'CONFIRM' to proceed with cleanup.",
            parse_mode='Markdown'
        )
        
        # Store cleanup data for confirmation
        context.user_data['cleanup_users'] = [user.id for user in inactive_users]
        context.user_data['cleanup_days'] = days
        context.user_data['cleanup_chat_id'] = chat_id
    
    finally:
        session.close()


async def handle_cleanup_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the 'CONFIRM' reply for /cleanup and actually kick the inactive
    users whose IDs were staged in user_data by cleanup_command.
    """
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip().upper()
    if text != 'CONFIRM':
        return

    chat_id = context.user_data.get('cleanup_chat_id')
    user_ids = context.user_data.get('cleanup_users')

    if not chat_id or not user_ids:
        await message.reply_text("ℹ️ No pending cleanup to confirm. Use `/cleanup <days>` first.")
        return

    # Verify the confirmer is an admin of the target chat.
    if not db.is_admin(update.effective_user.id, chat_id):
        await message.reply_text("❌ You need to be an admin to confirm cleanup.")
        return

    kicked = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.ban_chat_member(chat_id, uid)
            await context.bot.unban_chat_member(chat_id, uid)
            kicked += 1
        except Exception:
            failed += 1

    # Clear the staged cleanup so it cannot be triggered twice.
    context.user_data.pop('cleanup_users', None)
    context.user_data.pop('cleanup_chat_id', None)
    context.user_data.pop('cleanup_days', None)

    await message.reply_text(
        f"🧹 **Cleanup complete**\n\n"
        f"• Kicked: {kicked}\n"
        f"• Failed: {failed}",
        parse_mode='Markdown',
    )


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup chat settings as a real, importable JSON document.

    Produces a JSON file containing every per-chat setting the bot stores
    (notes, rules, filters, locks, allowlisted domains, welcome/goodbye
    settings, custom commands, admin IDs, warn mode, flood and raid settings)
    and sends it to the admin who requested it.
    """
    import json
    import io
    from handlers.notes import Note, Rule
    from handlers.filters import WordFilter, URLFilter, MediaFilter, URLAllowlist
    from handlers.welcome import WelcomeSettings
    from handlers.advanced_features import ChatSettings, CustomCommand
    from handlers.antiflood import get_flood_settings, get_raid_settings

    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        notes = [
            {'name': n.name, 'content': n.content, 'file_id': n.file_id, 'file_type': n.file_type}
            for n in session.query(Note).filter(Note.chat_id == chat_id).order_by(Note.name).all()
        ]
        rules = session.query(Rule).filter(Rule.chat_id == chat_id).first()
        word_filters = [
            {'word': f.word, 'action': f.action, 'is_regex': f.is_regex}
            for f in session.query(WordFilter).filter(WordFilter.chat_id == chat_id).all()
        ]
        url_filters = [
            {'domain': f.domain, 'action': f.action, 'is_whitelist': f.is_whitelist}
            for f in session.query(URLFilter).filter(URLFilter.chat_id == chat_id).all()
        ]
        media_filters = [
            {'media_type': f.media_type, 'is_locked': f.is_locked}
            for f in session.query(MediaFilter).filter(MediaFilter.chat_id == chat_id).all()
        ]
        allowlisted_domains = [
            r.domain for r in session.query(URLAllowlist).filter(URLAllowlist.chat_id == chat_id).all()
        ]
        welcome = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        chat_settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        custom_commands = [
            {'command': c.command, 'response': c.response}
            for c in session.query(CustomCommand).filter(CustomCommand.chat_id == chat_id).all()
        ]
        admin_ids = [a.user_id for a in db.get_chat_admins(chat_id)]
        warn_settings = db.get_warn_settings(chat_id)
        flood_settings = get_flood_settings(chat_id)
        raid_settings = get_raid_settings(chat_id)
    finally:
        session.close()

    def _welcome_dict(w):
        if not w:
            return None
        return {
            'welcome_enabled': w.welcome_enabled,
            'welcome_message': w.welcome_message,
            'welcome_media': w.welcome_media,
            'media_type': w.media_type,
            'delete_welcome': w.delete_welcome,
            'goodbye_enabled': w.goodbye_enabled,
            'goodbye_message': w.goodbye_message,
            'delete_joined_msg': w.delete_joined_msg,
            'delete_left_msg': w.delete_left_msg,
            'delete_all_system_msg': w.delete_all_system_msg,
            'delete_service': w.delete_service,
            'captcha_enabled': w.captcha_enabled,
            'captcha_time': w.captcha_time,
        }

    def _chat_settings_dict(c):
        if not c:
            return None
        return {
            'language': c.language,
            'timezone': c.timezone,
            'night_mode_enabled': c.night_mode_enabled,
            'night_mode_start': c.night_mode_start,
            'night_mode_end': c.night_mode_end,
            'slow_mode_enabled': c.slow_mode_enabled,
            'slow_mode_delay': c.slow_mode_delay,
            'antispam_enabled': c.antispam_enabled,
        }

    backup = {
        'bot': 'telegram-admin-bot',
        'backup_version': 1,
        'chat_id': chat_id,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'warn_settings': warn_settings,
        'flood_settings': flood_settings,
        'raid_settings': raid_settings,
        'admins': admin_ids,
        'notes': notes,
        'rules': rules.content if rules else None,
        'word_filters': word_filters,
        'url_filters': url_filters,
        'media_filters': media_filters,
        'allowlisted_domains': allowlisted_domains,
        'welcome_settings': _welcome_dict(welcome),
        'chat_settings': _chat_settings_dict(chat_settings),
        'custom_commands': custom_commands,
    }

    payload = json.dumps(backup, ensure_ascii=False, indent=2, default=str)
    filename = f"backup_{chat_id}.json"
    document = io.BytesIO(payload.encode('utf-8'))
    document.name = filename

    summary = (
        f"💾 **Backup generated**\n\n"
        f"• Notes: {len(notes)}\n"
        f"• Word filters: {len(word_filters)}\n"
        f"• Media locks: {len(media_filters)}\n"
        f"• Custom commands: {len(custom_commands)}\n"
        f"• Admins: {len(admin_ids)}\n"
        f"• Rules: {'✅' if rules else '❌'}\n"
        f"• Welcome settings: {'✅' if welcome else '❌'}"
    )

    try:
        await context.bot.send_document(
            chat_id,
            document=document,
            filename=filename,
            caption=summary,
        )
    except Exception as e:
        logger.error(f"Backup send failed: {e}")
        await update.message.reply_text(
            f"💾 **Backup generated**\n\n```\n{payload}\n```",
            parse_mode='Markdown',
        )


async def check_night_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if night mode restrictions apply"""
    if not update.message or not update.effective_user:
        return False
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip admins
    if db.is_admin(user_id, chat_id):
        return False
    
    session = db.get_session()
    try:
        settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        
        if not settings or not settings.night_mode_enabled:
            return False
        
        # Check if current time is in night mode
        now = datetime.now().time()
        start_time = datetime.strptime(settings.night_mode_start, '%H:%M').time()
        end_time = datetime.strptime(settings.night_mode_end, '%H:%M').time()
        
        # Handle overnight periods (e.g., 22:00 to 06:00)
        if start_time > end_time:
            is_night = now >= start_time or now <= end_time
        else:
            is_night = start_time <= now <= end_time
        
        if is_night:
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
                
                # Send warning (only once per user per night)
                warning_key = f"night_warning_{chat_id}_{user_id}"
                if warning_key not in night_mode_restrictions:
                    warning_msg = await context.bot.send_message(
                        chat_id,
                        f"🌙 {update.effective_user.first_name}, chat is in night mode. "
                        f"Only admins can send messages between {settings.night_mode_start} and {settings.night_mode_end}."
                    )
                    
                    # Delete warning after 10 seconds
                    context.job_queue.run_once(
                        lambda context: context.bot.delete_message(chat_id, warning_msg.message_id),
                        10
                    )
                    
                    night_mode_restrictions[warning_key] = True
                
                return True
            except Exception as e:
                logger.error(f"Error applying night mode restriction: {e}")
    
    finally:
        session.close()
    
    return False


async def check_slow_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Enforce slow mode for a chat. Returns True (and deletes the message) if the
    user sent another message before the configured delay elapsed. Admins and
    whitelisted users are exempt.
    """
    message = update.message or update.edited_message
    if not message or not update.effective_user:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id):
        return False

    session = db.get_session()
    try:
        settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        if not settings or not settings.slow_mode_enabled:
            return False
        delay = settings.slow_mode_delay or 30
    finally:
        session.close()

    now = datetime.now()
    per_chat = slow_mode_tracker.setdefault(chat_id, {})
    last = per_chat.get(user_id)

    if last is not None and (now - last).total_seconds() < delay:
        try:
            await context.bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return True

    per_chat[user_id] = now
    return False


# Initialize database
update_advanced_database()