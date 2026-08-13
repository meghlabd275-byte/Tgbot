"""
URL Remover module — mirrors the behaviour of @RemoveURLsBot / @RemoveSpamLinkBot /
@RemoveHyperlinkBot.

When `/removeurls on` is enabled for a chat, the bot automatically deletes ANY
message containing a URL or invite link (admins are exempt). This is a standalone
auto-remove mode separate from the per-domain url_filters table — it catches
*all* links, including t.me/ invites, @username links, bare domains, and links
inside photo/video captions. It also checks edited messages.
"""
import re
import logging
from urllib.parse import urlparse

from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime
from sqlalchemy.sql import func

from telegram import Update
from telegram.ext import ContextTypes
from database import Base, db
from database import db as database_instance
from utils import is_admin_command, is_group_command

logger = logging.getLogger(__name__)

# Per-chat URL-remover settings table
class URLRemoverSettings(Base):
    __tablename__ = 'url_remover_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    remove_urls = Column(Boolean, default=False)       # delete any web URL
    remove_invites = Column(Boolean, default=False)     # delete t.me / telegram invite links
    remove_all_links = Column(Boolean, default=False)  # delete everything link-like (urls + invites + @mentions-as-links)
    warn_user = Column(Boolean, default=False)         # also warn the user after deleting
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def update_url_remover_database():
    Base.metadata.create_all(bind=database_instance.engine)


# ---------------------------------------------------------------------------
# Link detection patterns
# ---------------------------------------------------------------------------

# Full URLs: http(s)://anything, www.something, ftp://
URL_REGEX = re.compile(
    r'(?:https?|ftp)://[^\s<>"\']+|www\.[^\s<>"\']+',
    re.IGNORECASE,
)

# Telegram invite / t.me links (also catches t.me/joinchat, t.me/+hash, t.me/channelname)
TELEGRAM_INVITE_REGEX = re.compile(
    r'(?:https?://)?t(?:elegram)?\.me/(?:joinchat/|\+)?[^\s<>"\']+|@(?P<uname>[A-Za-z][A-Za-z0-9_]{3,31})',
    re.IGNORECASE,
)

# Bare-domain detection (e.g. "example.com/path") that isn't part of a normal word.
# Looks for a dot surrounded by alnum chars with a TLD-like suffix.
BARE_DOMAIN_REGEX = re.compile(
    r'\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
    r'\.[a-zA-Z]{2,}(?:/[^\s<>"\']*)?\b'
)

# Common TLDs to reduce false positives for bare-domain matching
COMMON_TLDS = {
    'com', 'net', 'org', 'io', 'co', 'me', 'app', 'dev', 'info', 'biz',
    'xyz', 'online', 'site', 'tech', 'store', 'blog', 'tv', 'gg', 'live',
    'news', 'shop', 'link', 'click', 'top', 'fun', 'club', 'world', 'space',
    'pro', 'ai', 'gov', 'edu', 'mil', 'int', 'ru', 'de', 'uk', 'us', 'ca',
    'au', 'fr', 'es', 'it', 'nl', 'se', 'no', 'fi', 'dk', 'br', 'in', 'cn',
    'jp', 'kr', 'ir', 'pk', 'bd', 'id', 'ph', 'vn', 'th', 'my', 'sg', 'hk',
    'tw', 'sa', 'ae', 'eg', 'za', 'ng', 'ke', 'tz', 'ua', 'pl', 'cz', 'sk',
    'hu', 'ro', 'bg', 'gr', 'tr', 'il', 'pt', 'ch', 'at', 'be', 'ie', 'lu',
}


def extract_text(message) -> str:
    """Return the text body of a message — either text or media caption."""
    if message is None:
        return ''
    return message.text or message.caption or ''


def _extract_entity_urls(message) -> list:
    """
    Return URLs found in message entities / caption_entities.

    Telegram reports URLs as entities of type 'url' (visible) and
    'text_link' (hidden behind a hyperlink, e.g. "click here" -> url).
    A user can bypass regex-based detection by hiding a URL behind a
    text_link entity, so we must inspect entities too.
    """
    urls = []
    if message is None:
        return urls
    entities = list(getattr(message, 'entities', None) or []) + \
                list(getattr(message, 'caption_entities', None) or [])
    for ent in entities:
        etype = getattr(ent, 'type', None)
        if etype == 'text_link':
            url = getattr(ent, 'url', None)
            if url:
                urls.append(url)
        elif etype == 'url' and message.text:
            # Visible URL entity: extract the substring from the text.
            try:
                urls.append(message.text[ent.offset:ent.offset + ent.length])
            except Exception:
                pass
        elif etype == 'url' and message.caption:
            try:
                urls.append(message.caption[ent.offset:ent.offset + ent.length])
            except Exception:
                pass
    return urls


def contains_url(text: str) -> bool:
    """True if the text contains any web URL (http(s)://, www., or bare domain)."""
    if not text:
        return False
    if URL_REGEX.search(text):
        return True
    # bare domain only if TLD is in our known set (reduces false positives)
    for m in BARE_DOMAIN_REGEX.finditer(text):
        domain_part = m.group(0).split('/')[0]
        tld = domain_part.rsplit('.', 1)[-1].lower()
        if tld in COMMON_TLDS:
            return True
    return False


def contains_invite_link(text: str) -> bool:
    """True if the text contains a Telegram invite / t.me link or @channel mention."""
    if not text:
        return False
    return bool(TELEGRAM_INVITE_REGEX.search(text))


def message_has_link(message) -> bool:
    """
    True if the message contains a URL or invite link in its text, caption,
    OR hidden inside message/caption entities (text_link / url entities).
    """
    text = extract_text(message)
    if contains_url(text) or contains_invite_link(text):
        return True
    # Check hidden URLs in entities (text_link = hyperlink with hidden URL)
    for url in _extract_entity_urls(message):
        if contains_url(url) or contains_invite_link(url):
            return True
    return False


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def get_settings(chat_id: int):
    session = db.get_session()
    try:
        s = session.query(URLRemoverSettings).filter(URLRemoverSettings.chat_id == chat_id).first()
        return s, session
    except Exception:
        session.close()
        return None, session


def is_url_removal_active(chat_id: int) -> bool:
    """Quick check whether any URL-removal mode is active for this chat."""
    session = db.get_session()
    try:
        s = session.query(URLRemoverSettings).filter(URLRemoverSettings.chat_id == chat_id).first()
        if not s:
            return False
        return bool(s.remove_urls or s.remove_invites or s.remove_all_links)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Core filter check (called from check_message_filters / edited message handler)
# ---------------------------------------------------------------------------

async def check_url_remover(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Returns True (and deletes the message) if a URL-removal rule applies.
    Admins and whitelisted users are always exempt.
    """
    # Normalize: edited messages arrive as update.edited_message
    message = update.message or update.edited_message
    if not message or not update.effective_user:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Exempt admins & whitelisted users
    if db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id):
        return False

    session = db.get_session()
    try:
        s = session.query(URLRemoverSettings).filter(URLRemoverSettings.chat_id == chat_id).first()
        if not s:
            return False

        if not (s.remove_urls or s.remove_invites or s.remove_all_links):
            return False

        text = extract_text(message)

        should_delete = False
        reason = ''

        if s.remove_all_links:
            # Catches URLs/invites in text, captions, AND hidden hyperlinks (entities)
            if message_has_link(message):
                should_delete = True
                reason = 'link detected (remove-all-links mode)'
        else:
            if s.remove_urls and (contains_url(text) or any(contains_url(u) for u in _extract_entity_urls(message))):
                should_delete = True
                reason = 'URL detected (remove-urls mode)'
            if not should_delete and s.remove_invites and \
               (contains_invite_link(text) or any(contains_invite_link(u) for u in _extract_entity_urls(message))):
                should_delete = True
                reason = 'invite link detected (remove-invites mode)'

        if not should_delete:
            return False

        # Delete the offending message
        try:
            await context.bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            logger.error(f"URL remover: failed to delete message in {chat_id}: {e}")
            return False

        # Optionally warn
        if s.warn_user:
            try:
                db.add_warning(user_id, chat_id, context.bot.id, reason)
                count = db.get_warnings_count(user_id, chat_id)
                await context.bot.send_message(
                    chat_id,
                    f"⚠️ {update.effective_user.first_name}, links are not allowed here. "
                    f"Warning {count}/3"
                )
            except Exception as e:
                logger.error(f"URL remover: failed to warn user: {e}")

        logger.info(f"URL remover deleted message from {user_id} in {chat_id}: {reason}")
        return True
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@is_admin_command
@is_group_command
async def removeurls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Toggle auto-removal of web URLs (http(s)://, www., bare domains).
    Usage:
      /removeurls on            -> remove all web URLs
      /removeurls off           -> disable
      /removeurls invites on    -> also remove t.me / telegram invite links
      /removeurls all on        -> remove everything link-like (urls + invites + @links)
      /removeurls warn on|off   -> also warn the sender
      /removeurls status        -> show current settings
    """
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "🔗 **URL Remover** — auto-delete messages containing links\n\n"
            "**Commands:**\n"
            "• `/removeurls on` — delete messages with web URLs\n"
            "• `/removeurls off` — disable URL removal\n"
            "• `/removeurls invites on|off` — remove Telegram invite/t.me links\n"
            "• `/removeurls all on|off` — remove all link types (urls + invites + @links)\n"
            "• `/removeurls warn on|off` — also warn the sender\n"
            "• `/removeurls status` — show current settings\n\n"
            "Admins are always exempt. Works on text and photo/video captions, "
            "and checks edited messages too.",
            parse_mode='Markdown',
        )
        return

    sub = context.args[0].lower()
    session = db.get_session()
    try:
        s = session.query(URLRemoverSettings).filter(URLRemoverSettings.chat_id == chat_id).first()
        if not s:
            s = URLRemoverSettings(chat_id=chat_id)
            session.add(s)

        def _bool(val: str) -> bool:
            return val.lower() in ('on', 'yes', 'true', '1')

        if sub == 'status':
            await update.message.reply_text(
                "🔗 **URL Remover Settings**\n\n"
                f"• Remove URLs: {'✅' if s.remove_urls else '❌'}\n"
                f"• Remove Invites: {'✅' if s.remove_invites else '❌'}\n"
                f"• Remove All Links: {'✅' if s.remove_all_links else '❌'}\n"
                f"• Warn User: {'✅' if s.warn_user else '❌'}",
                parse_mode='Markdown',
            )
            return

        if sub == 'on':
            s.remove_urls = True
            msg = "✅ URL removal enabled. Messages with web URLs will be deleted (admins exempt)."
        elif sub == 'off':
            s.remove_urls = False
            s.remove_invites = False
            s.remove_all_links = False
            msg = "✅ URL removal disabled."
        elif sub == 'invites':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/removeurls invites on|off`", parse_mode='Markdown')
                return
            s.remove_invites = _bool(context.args[1])
            msg = f"✅ Invite-link removal {'enabled' if s.remove_invites else 'disabled'}."
        elif sub == 'all':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/removeurls all on|off`", parse_mode='Markdown')
                return
            s.remove_all_links = _bool(context.args[1])
            msg = f"✅ Remove-all-links mode {'enabled' if s.remove_all_links else 'disabled'}."
        elif sub == 'warn':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/removeurls warn on|off`", parse_mode='Markdown')
                return
            s.warn_user = _bool(context.args[1])
            msg = f"✅ Warning on link removal {'enabled' if s.warn_user else 'disabled'}."
        else:
            await update.message.reply_text(
                "❌ Unknown option. Use: on, off, invites, all, warn, status", parse_mode='Markdown'
            )
            return

        session.commit()
        await update.message.reply_text(msg, parse_mode='Markdown')
    finally:
        session.close()


# Initialize the table
update_url_remover_database()
