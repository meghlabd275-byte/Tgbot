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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Federation(Base):
    __tablename__ = 'federations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36), unique=True)  # UUID
    name = Column(String(255))
    owner_id = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

class FederationChat(Base):
    __tablename__ = 'federation_chats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    chat_id = Column(BigInteger)
    joined_by = Column(BigInteger)
    joined_at = Column(DateTime, default=func.now())

class FederationBan(Base):
    __tablename__ = 'federation_bans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    user_id = Column(BigInteger)
    banned_by = Column(BigInteger)
    reason = Column(Text)
    created_at = Column(DateTime, default=func.now())

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
    
    finally:
        session.close()

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup chat settings"""
    chat_id = update.effective_chat.id
    
    # This would generate a backup file with all chat settings
    # For now, just show what would be backed up
    
    session = db.get_session()
    try:
        # Count various settings
        notes_count = session.query(db.Note).filter(db.Note.chat_id == chat_id).count()
        filters_count = session.query(db.WordFilter).filter(db.WordFilter.chat_id == chat_id).count()
        admins_count = session.query(db.Admin).filter(db.Admin.chat_id == chat_id).count()
        
        backup_info = f"""💾 **Backup Information**

**Chat ID:** `{chat_id}`
**Backup Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Data to backup:**
• Notes: {notes_count}
• Word Filters: {filters_count}
• Bot Admins: {admins_count}
• Welcome/Goodbye Settings
• Chat Settings
• Reports History

**Note:** Full backup/restore functionality coming soon!"""
        
        await update.message.reply_text(backup_info, parse_mode='Markdown')
    
    finally:
        session.close()

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

# Initialize database
update_advanced_database()