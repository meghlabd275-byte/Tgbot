from telegram import Update, ChatPermissions
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

class URLAllowlist(Base):
    __tablename__ = 'url_allowlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    domain = Column(String(255))
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())

# Recreate database with new tables
def update_database():
    Base.metadata.create_all(bind=database_instance.engine)


# Emoji Unicode ranges (emoticons, pictographs, symbols, and »flags»).
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # emoticons, misc symbols, pictographs, transport
    "\U00002600-\U000027BF"  # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicator symbols (flags)
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U00002190-\U000021FF"  # arrows
    "\U00002B00-\U00002BFF"  # misc symbols and arrows
    "]+"
)


def _contains_emoji(text: str) -> bool:
    """Return True if the text contains at least one emoji character."""
    if not text:
        return False
    return bool(_EMOJI_PATTERN.search(text))

# All lockable message types (mirrors Rose's /locktypes)
LOCK_TYPES = [
    'url', 'invite', 'forward', 'photo', 'video', 'audio', 'voice',
    'document', 'sticker', 'gif', 'animation', 'video_note', 'contact',
    'location', 'poll', 'reply', 'game', 'emoji', 'text',
]

LOCK_DESCRIPTIONS = {
    'url': 'Messages containing web URLs',
    'invite': 'Telegram invite (t.me) links',
    'forward': 'Forwarded messages',
    'photo': 'Photo messages',
    'video': 'Video messages',
    'audio': 'Audio messages',
    'voice': 'Voice notes',
    'document': 'Files / documents',
    'sticker': 'Stickers',
    'gif': 'GIFs / animations',
    'animation': 'Animations',
    'video_note': 'Round (video) messages',
    'contact': 'Contact cards',
    'location': 'Location shares',
    'poll': 'Polls',
    'reply': 'Replies to other messages',
    'game': 'Games',
    'emoji': 'Messages containing emojis',
    'text': 'Plain text messages',
}

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
    """Lock one or more message types (e.g. /lock url gif sticker)"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/lock <type>`\n"
            f"Types: {', '.join(LOCK_TYPES)}\n\n"
            "You can lock several at once: `/lock url gif sticker`\n"
            "See all types with `/locktypes`.",
            parse_mode='Markdown'
        )
        return

    requested = [a.lower().strip() for a in context.args]
    invalid = [t for t in requested if t not in LOCK_TYPES]
    if invalid:
        await update.message.reply_text(
            f"❌ Invalid type(s): {', '.join(invalid)}\n"
            f"Valid types: {', '.join(LOCK_TYPES)}"
        )
        return

    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id

    session = db.get_session()
    try:
        for media_type in requested:
            existing = session.query(MediaFilter).filter(
                MediaFilter.chat_id == chat_id,
                MediaFilter.media_type == media_type
            ).first()

            if existing:
                existing.is_locked = True
            else:
                session.add(MediaFilter(
                    chat_id=chat_id,
                    media_type=media_type,
                    is_locked=True,
                    created_by=admin_id
                ))
        session.commit()
        await update.message.reply_text(f"🔒 Locked: {', '.join(requested)}")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock one or more message types"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/unlock <type>`")
        return

    requested = [a.lower().strip() for a in context.args]
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        for media_type in requested:
            media_filter = session.query(MediaFilter).filter(
                MediaFilter.chat_id == chat_id,
                MediaFilter.media_type == media_type
            ).first()

            if media_filter:
                media_filter.is_locked = False
        session.commit()
        await update.message.reply_text(f"🔓 Unlocked: {', '.join(requested)}")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def locks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current locks (or full lock status list)."""
    chat_id = update.effective_chat.id
    show_all = bool(context.args) and context.args[0].lower() == 'list'

    session = db.get_session()
    try:
        rows = session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id
        ).all()
        locked_map = {r.media_type: r.is_locked for r in rows}

        if show_all:
            msg = "🔒 **Lock Status (all types):**\n\n"
            for t in LOCK_TYPES:
                status = '🔒 locked' if locked_map.get(t) else '🔓 unlocked'
                desc = LOCK_DESCRIPTIONS.get(t, '')
                msg += f"• `{t}` — {status}"
                if desc:
                    msg += f" ({desc})"
                msg += "\n"
        else:
            locked = [t for t in LOCK_TYPES if locked_map.get(t)]
            if not locked:
                await update.message.reply_text("🔓 No message types are currently locked.")
                return
            msg = "🔒 **Locked Message Types:**\n\n"
            for t in locked:
                msg += f"• {t}\n"
            msg += "\nUse `/locks list` to see all types."

        await update.message.reply_text(msg, parse_mode='Markdown')
    finally:
        session.close()


@is_admin_command
@is_group_command
async def locktypes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all lockable message types with descriptions."""
    msg = "🔒 **Available Lock Types:**\n\n"
    for t in LOCK_TYPES:
        msg += f"**{t}** — {LOCK_DESCRIPTIONS.get(t, '')}\n"
    msg += "\nUsage: `/lock <type>` / `/unlock <type>` / `/locks list`"
    await update.message.reply_text(msg, parse_mode='Markdown')


@is_admin_command
@is_group_command
async def allowlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allowlist URLs/domains so they bypass lock url / URL removal."""
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        if not context.args:
            rows = session.query(URLAllowlist).filter(URLAllowlist.chat_id == chat_id).all()
            if not rows:
                await update.message.reply_text("📋 No allowlisted domains.")
                return
            msg = "✅ **Allowlisted Domains:**\n\n"
            for r in rows:
                msg += f"• {r.domain}\n"
            await update.message.reply_text(msg, parse_mode='Markdown')
            return

        domain = re.sub(r'^https?://', '', context.args[0]).strip().strip('/')
        if not domain:
            await update.message.reply_text("❌ Invalid domain.")
            return

        existing = session.query(URLAllowlist).filter(
            URLAllowlist.chat_id == chat_id,
            URLAllowlist.domain == domain
        ).first()

        if existing:
            await update.message.reply_text("ℹ️ That domain is already allowlisted.")
        else:
            session.add(URLAllowlist(chat_id=chat_id, domain=domain, created_by=update.effective_user.id))
            session.commit()
            await update.message.reply_text(f"✅ Allowlisted `{domain}`. Lock url / URL removal will ignore it.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def unallowlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("❌ Usage: `/unallowlist <domain>`")
        return

    domain = re.sub(r'^https?://', '', context.args[0]).strip().strip('/')
    session = db.get_session()
    try:
        row = session.query(URLAllowlist).filter(
            URLAllowlist.chat_id == chat_id,
            URLAllowlist.domain == domain
        ).first()
        if row:
            session.delete(row)
            session.commit()
            await update.message.reply_text(f"✅ Removed `{domain}` from the allowlist.")
        else:
            await update.message.reply_text("❌ That domain is not allowlisted.")
    finally:
        session.close()


def is_domain_allowlisted(chat_id: int, domain: str) -> bool:
    session = db.get_session()
    try:
        domain = domain.lower()
        rows = session.query(URLAllowlist).filter(URLAllowlist.chat_id == chat_id).all()
        for r in rows:
            allowed = r.domain.lower()
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        return False
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
    
    from handlers.advanced_features import ChatSettings
    session = db.get_session()
    try:
        settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        if settings:
            settings.antispam_enabled = status
            session.commit()
        else:
            settings = ChatSettings(chat_id=chat_id, antispam_enabled=status)
            session.add(settings)
            session.commit()
        await update.message.reply_text(
            f"✅ Anti-spam protection {'enabled' if status else 'disabled'}."
        )
    finally:
        session.close()

async def check_message_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against all filters"""
    # Normalize: edited messages arrive as update.edited_message (update.message is None)
    message = update.message or update.edited_message
    if not message or not update.effective_user:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Skip admins, whitelisted and approved users
    if (db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id)
            or db.is_approved(user_id, chat_id)):
        return False

    # --- URL Remover (auto-remove all URLs/invites) - checks text AND captions ---
    try:
        from handlers.url_remover import check_url_remover
        if await check_url_remover(update, context):
            return True
    except Exception as e:
        logger.error(f"URL remover check failed: {e}")

    # Text to check (includes captions for media messages)
    text_to_check = message.text or message.caption or ''

    # Check word filters
    if text_to_check:
        if await check_word_filters(update, context):
            return True

    # Check URL filters (domain-based blocklist)
    if text_to_check and ('http' in text_to_check or 'www.' in text_to_check or 't.me' in text_to_check):
        if await check_url_filters(update, context):
            return True

    # Check media filters
    if await check_media_filters(update, context):
        return True

    # Check spam patterns (only if anti-spam is enabled for this chat)
    if text_to_check and is_antispam_enabled(chat_id) and await check_spam_patterns(update, context):
        return True

    return False

def is_antispam_enabled(chat_id: int) -> bool:
    """Check if anti-spam (spam pattern detection) is enabled for a chat"""
    from handlers.advanced_features import ChatSettings
    session = db.get_session()
    try:
        settings = session.query(ChatSettings).filter(ChatSettings.chat_id == chat_id).first()
        # Default to enabled when no settings row exists yet
        return settings.antispam_enabled if settings else True
    finally:
        session.close()

async def check_word_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against word filters"""
    chat_id = update.effective_chat.id
    _msg = update.message or update.edited_message
    message_text = (_msg.text or _msg.caption or '').lower()
    
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
    _msg = update.message or update.edited_message
    message_text = _msg.text or _msg.caption or ''
    
    # Extract URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message_text)
    
    if not urls:
        return False
    
    session = db.get_session()
    try:
        url_filters = session.query(URLFilter).filter(URLFilter.chat_id == chat_id).all()
        
        for url in urls:
            domain = urlparse(url).netloc.lower()
            if not domain:
                continue

            # Allowlisted domains always pass
            if is_domain_allowlisted(chat_id, domain):
                continue

            # Check against suspicious domains
            if domain in SUSPICIOUS_DOMAINS:
                await apply_filter_action(update, context, 'delete', f"Suspicious shortened URL: {domain}")
                return True
            
            # Check against custom filters
            for url_filter in url_filters:
                if url_filter.domain in domain or domain in url_filter.domain:
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
    message = update.message or update.edited_message
    
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
    elif message.animation:
        media_type = 'animation'  # animation (GIF) maps to both 'gif' and 'animation'
    elif message.voice:
        media_type = 'voice'
    elif message.video_note:
        media_type = 'video_note'
    elif message.audio:
        media_type = 'audio'
    elif message.contact:
        media_type = 'contact'
    elif message.location:
        media_type = 'location'
    elif message.poll:
        media_type = 'poll'
    elif message.game:
        media_type = 'game'
    elif message.forward_from or message.forward_from_chat:
        media_type = 'forward'
    elif message.reply_to_message:
        media_type = 'reply'

    def _locked(session, t):
        return session.query(MediaFilter).filter(
            MediaFilter.chat_id == chat_id,
            MediaFilter.media_type == t,
            MediaFilter.is_locked == True
        ).first() is not None

    session = db.get_session()
    try:
        text_for_url = message.text or message.caption or ''
        if text_for_url:
            from handlers.url_remover import contains_invite_link

            # 'url' lock: delete messages containing URLs (unless allowlisted)
            if _locked(session, 'url') and ('http' in text_for_url or 'www.' in text_for_url):
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text_for_url)
                fully_allowlisted = bool(urls) and all(
                    is_domain_allowlisted(chat_id, urlparse(u).netloc.lower()) for u in urls)
                if not fully_allowlisted:
                    await apply_filter_action(update, context, 'delete', "Locked media type: url")
                    return True

            # 'invite' lock: delete messages containing t.me / telegram invite links
            if _locked(session, 'invite') and contains_invite_link(text_for_url):
                await apply_filter_action(update, context, 'delete', "Locked media type: invite")
                return True

            # 'emoji' lock: delete messages containing emoji characters
            if _locked(session, 'emoji') and _contains_emoji(text_for_url):
                await apply_filter_action(update, context, 'delete', "Locked media type: emoji")
                return True

            # 'text' lock: delete plain text messages (no media attached)
            if _locked(session, 'text') and message.text and not any([
                message.photo, message.video, message.document, message.sticker,
                message.animation, message.voice, message.video_note, message.audio,
                message.contact, message.location, message.poll, message.game,
                message.forward_from, message.forward_from_chat, message.reply_to_message,
            ]):
                await apply_filter_action(update, context, 'delete', "Locked media type: text")
                return True

        # 'game' lock: delete game messages (game has no separate text check above)
        if media_type == 'game' and _locked(session, 'game'):
            await apply_filter_action(update, context, 'delete', "Locked media type: game")
            return True

        if media_type == 'animation':
            # gif and animation are semantically identical here
            for t in ('animation', 'gif'):
                if _locked(session, t):
                    await apply_filter_action(update, context, 'delete', f"Locked media type: {t}")
                    return True
        elif media_type and media_type not in ('game',) and _locked(session, media_type):
            await apply_filter_action(update, context, 'delete', f"Locked media type: {media_type}")
            return True

    finally:
        session.close()

    return False


async def check_spam_patterns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check message against spam patterns"""
    _msg = update.message or update.edited_message
    message_text = _msg.text or _msg.caption or ''
    
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
        # Always delete the message first (works for both normal and edited messages)
        msg = update.effective_message
        await context.bot.delete_message(chat_id, msg.message_id)
        
        if action == 'warn':
            db.add_warning(user_id, chat_id, context.bot.id, reason)
            warning_count = db.get_warnings_count(user_id, chat_id)

            settings = db.get_warn_settings(chat_id)
            extra = ""
            if warning_count >= settings['limit']:
                from handlers.moderation import apply_warn_consequence
                consequence = await apply_warn_consequence(chat_id, user_id, context.bot.id, context)
                if consequence:
                    extra = f"\n🚨 User has been {consequence} for reaching the warning limit!"

            action_msg = await context.bot.send_message(
                chat_id,
                f"⚠️ {user.first_name} warned for: {reason}\n"
                f"Warnings: {warning_count}/{settings['limit']}{extra}"
            )


        elif action == 'mute':
            from datetime import datetime, timedelta
            until_date = datetime.now() + timedelta(hours=1)
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
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