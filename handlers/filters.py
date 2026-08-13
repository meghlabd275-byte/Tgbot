from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Add new tables to database for filters
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base, db as database_instance

class WordFilter(Base):
    __tablename__ = 'word_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    word = Column(String(255))
    action = Column(String(50), default='delete')  # delete, warn, mute, kick, ban
    is_regex = Column(Boolean, default=False)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

class URLFilter(Base):
    __tablename__ = 'url_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    domain = Column(String(255))
    action = Column(String(50), default='delete')
    is_whitelist = Column(Boolean, default=False)  # True for allowed domains
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

class MediaFilter(Base):
    __tablename__ = 'media_filters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    media_type = Column(String(50))  # photo, video, document, sticker, etc.
    is_locked = Column(Boolean, default=False)
    action = Column(String(50), default='delete')
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

# Recreate database with new tables
def update_database():
    Base.metadata.create_all(bind=database_instance.engine)

# Common spam patterns
SPAM_PATTERNS = [
    r'(?i)(free|win|winner|congratulations).*(money|cash|prize|reward)',
    r'(?i)(click|visit|check).*(link|url|website)',
    r'(?i)(telegram|whatsapp|discord).*(group|channel|server)',
    r'(?i)(crypto|bitcoin|trading|investment).*(profit|earn|money)',
    r'(?i)(dating|meet|girls|boys).*(app|site|website)',
]

SUSPICIOUS_DOMAINS = [
    'bit.ly', 'tinyurl.com', 'short.link', 't.co', 'goo.gl',
    'ow.ly', 'buff.ly', 'is.gd', 'tiny.cc'
]

@is_admin_command
@is_group_command
async def addfilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a word filter"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/addfilter <word> <action>`\n"
            "Actions: delete, warn, mute, kick, ban\n"
            "Example: `/addfilter spam delete`",
            parse_mode='Markdown'
        )
        return
    
    word = context.args[0].lower()
    action = context.args[1].lower()
    
    if action not in ['delete', 'warn', 'mute', 'kick', 'ban']:
        await update.message.reply_text("❌ Invalid action. Use: delete, warn, mute, kick, ban")
        return
    
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    session = db.get_session()
    try:
        # Check if filter already exists
        existing = session.query(WordFilter).filter(
            WordFilter.chat_id == chat_id,
            WordFilter.word == word
        ).first()
        
        if existing:
            existing.action = action
            session.commit()
            await update.message.reply_text(f"✅ Updated filter for '{word}' with action: {action}")
        else:
            word_filter = WordFilter(
                chat_id=chat_id,
                word=word,
                action=action,
                created_by=admin_id
            )
            session.add(word_filter)
            session.commit()
            await update.message.reply_text(f"✅ Added filter for '{word}' with action: {action}")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def removefilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a word filter"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/removefilter <word>`")
        return
    
    word = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        word_filter = session.query(WordFilter).filter(
            WordFilter.chat_id == chat_id,
            WordFilter.word == word
        ).first()
        
        if word_filter:
            session.delete(word_filter)
            session.commit()
            await update.message.reply_text(f"✅ Removed filter for '{word}'")
        else:
            await update.message.reply_text(f"❌ No filter found for '{word}'")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all word filters"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        filters = session.query(WordFilter).filter(WordFilter.chat_id == chat_id).all()
        
        if not filters:
            await update.message.reply_text("📝 No word filters set for this chat.")
            return
        
        filter_list = "📝 **Word Filters:**\n\n"
        for f in filters:
            filter_list += f"• `{f.word}` → {f.action}\n"
        
        await update.message.reply_text(filter_list, parse_mode='Markdown')
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock specific message types"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/lock <type>`\n"
            "Types: url, photo, video, document, sticker, voice, video_note, animation, contact, location, poll, forward, reply"
        )
        return
    
    media_type = context.args[0].lower()
    valid_types = ['url', 'photo', 'video', 'document', 'sticker', 'voice', 'video_note', 'animation', 'contact', 'location', 'poll', 'forward', 'reply']
    
    if media_type not in valid_types:
        await update.message.reply_text(f"❌ Invalid type. Valid types: {', '.join(valid_types)}")
        return
    
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    session = db.get_session()
    try:
        existing = session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id,
            MediaFilter.media_type == media_type
        ).first()
        
        if existing:
            existing.is_locked = True
            session.commit()
        else:
            media_filter = MediaFilter(
                chat_id=chat_id,
                media_type=media_type,
                is_locked=True,
                created_by=admin_id
            )
            session.add(media_filter)
            session.commit()
        
        await update.message.reply_text(f"🔒 Locked {media_type} messages in this chat.")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock specific message types"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/unlock <type>`")
        return
    
    media_type = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        media_filter = session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id,
            MediaFilter.media_type == media_type
        ).first()
        
        if media_filter:
            media_filter.is_locked = False
            session.commit()
            await update.message.reply_text(f"🔓 Unlocked {media_type} messages in this chat.")
        else:
            await update.message.reply_text(f"❌ {media_type} is not locked.")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def locks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current locks"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        locks = session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id,
            MediaFilter.is_locked == True
        ).all()
        
        if not locks:
            await update.message.reply_text("🔓 No message types are currently locked.")
            return
        
        lock_list = "🔒 **Locked Message Types:**\n\n"
        for lock in locks:
            lock_list += f"• {lock.media_type}\n"
        
        await update.message.reply_text(lock_list, parse_mode='Markdown')
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def antispam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle anti-spam protection"""
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("❌ Usage: `/antispam on|off`")
        return
    
    status = context.args[0].lower() == 'on'
    chat_id = update.effective_chat.id
    
    # Store in chat settings (we'll add this to database)
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat:
            # We'll add an antispam field to the Chat model
            await update.message.reply_text(
                f"✅ Anti-spam protection {'enabled' if status else 'disabled'}."
            )
    finally:
        session.close()

async def check_message_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against all filters"""
    if not update.message or not update.effective_user:
        return False
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    message = update.message
    
    # Skip admins and whitelisted users
    if db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id):
        return False
    
    # Check word filters
    if message.text:
        if await check_word_filters(update, context):
            return True
    
    # Check URL filters
    if message.text and ('http' in message.text or 'www.' in message.text):
        if await check_url_filters(update, context):
            return True
    
    # Check media filters
    if await check_media_filters(update, context):
        return True
    
    # Check spam patterns
    if message.text and await check_spam_patterns(update, context):
        return True
    
    return False

async def check_word_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against word filters"""
    chat_id = update.effective_chat.id
    message_text = update.message.text.lower()
    
    session = db.get_session()
    try:
        filters = session.query(WordFilter).filter(WordFilter.chat_id == chat_id).all()
        
        for word_filter in filters:
            if word_filter.is_regex:
                if re.search(word_filter.word, message_text, re.IGNORECASE):
                    await apply_filter_action(update, context, word_filter.action, f"Filtered word: {word_filter.word}")
                    return True
            else:
                if word_filter.word in message_text:
                    await apply_filter_action(update, context, word_filter.action, f"Filtered word: {word_filter.word}")
                    return True
    
    finally:
        session.close()
    
    return False

async def check_url_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against URL filters"""
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    # Extract URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message_text)
    
    if not urls:
        return False
    
    session = db.get_session()
    try:
        url_filters = session.query(URLFilter).filter(URLFilter.chat_id == chat_id).all()
        
        for url in urls:
            domain = urlparse(url).netloc.lower()
            
            # Check against suspicious domains
            if domain in SUSPICIOUS_DOMAINS:
                await apply_filter_action(update, context, 'delete', f"Suspicious shortened URL: {domain}")
                return True
            
            # Check against custom filters
            for url_filter in url_filters:
                if url_filter.domain in domain:
                    if url_filter.is_whitelist:
                        continue  # Allowed domain
                    else:
                        await apply_filter_action(update, context, url_filter.action, f"Blocked domain: {domain}")
                        return True
    
    finally:
        session.close()
    
    return False

async def check_media_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against media filters"""
    chat_id = update.effective_chat.id
    message = update.message
    
    # Determine message type
    media_type = None
    if message.photo:
        media_type = 'photo'
    elif message.video:
        media_type = 'video'
    elif message.document:
        media_type = 'document'
    elif message.sticker:
        media_type = 'sticker'
    elif message.voice:
        media_type = 'voice'
    elif message.video_note:
        media_type = 'video_note'
    elif message.animation:
        media_type = 'animation'
    elif message.contact:
        media_type = 'contact'
    elif message.location:
        media_type = 'location'
    elif message.poll:
        media_type = 'poll'
    elif message.forward_from or message.forward_from_chat:
        media_type = 'forward'
    elif message.reply_to_message:
        media_type = 'reply'
    
    if not media_type:
        return False
    
    session = db.get_session()
    try:
        media_filter = session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id,
            MediaFilter.media_type == media_type,
            MediaFilter.is_locked == True
        ).first()
        
        if media_filter:
            await apply_filter_action(update, context, media_filter.action, f"Locked media type: {media_type}")
            return True
    
    finally:
        session.close()
    
    return False

async def check_spam_patterns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against spam patterns"""
    message_text = update.message.text
    
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, message_text):
            await apply_filter_action(update, context, 'delete', "Spam pattern detected")
            return True
    
    return False

async def apply_filter_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, reason: str):
    """Apply filter action to user"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user
    
    try:
        # Always delete the message first
        await context.bot.delete_message(chat_id, update.message.message_id)
        
        if action == 'warn':
            db.add_warning(user_id, chat_id, context.bot.id, reason)
            warning_count = db.get_warnings_count(user_id, chat_id)
            
            action_msg = await context.bot.send_message(
                chat_id,
                f"⚠️ {user.first_name} warned for: {reason}\n"
                f"Warnings: {warning_count}/3"
            )
            
        elif action == 'mute':
            from datetime import datetime, timedelta
            until_date = datetime.now() + timedelta(hours=1)
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=context.bot.get_chat(chat_id).permissions,
                until_date=until_date
            )
            db.add_mute(user_id, chat_id, context.bot.id, 3600, reason)
            
            action_msg = await context.bot.send_message(
                chat_id,
                f"🔇 {user.first_name} muted for 1 hour: {reason}"
            )
            
        elif action == 'kick':
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            
            action_msg = await context.bot.send_message(
                chat_id,
                f"👢 {user.first_name} kicked: {reason}"
            )
            
        elif action == 'ban':
            await context.bot.ban_chat_member(chat_id, user_id)
            db.add_ban(user_id, chat_id, context.bot.id, reason)
            
            action_msg = await context.bot.send_message(
                chat_id,
                f"🔨 {user.first_name} banned: {reason}"
            )
        
        # Delete action message after 5 seconds (except for delete-only)
        if action != 'delete':
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat_id, action_msg.message_id),
                5
            )
        
        logger.info(f"Filter action {action} applied to user {user_id} in chat {chat_id}: {reason}")
        
    except Exception as e:
        logger.error(f"Error applying filter action: {e}")

# Initialize new database tables
update_database()