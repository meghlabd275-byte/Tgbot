"""
Quick Replies module — admin-configured auto-replies and greeting cleanup.

Three independent features:

1. **Contract addresses (CA)** — group admins register one or more
   ``(network, address)`` pairs. When a member sends ``CA`` / ``ca`` / ``cA`` /
   ``Ca`` (or "contract" / "contract address") the bot replies with every
   configured contract address and its network.

2. **Keyword links** — group admins register keyword -> link pairs (e.g.
   "website", "contact", "proposal"). When a member's message contains a
   configured keyword, the bot replies with the link as an inline button.

3. **Greeting auto-delete** — group admins can enable automatic deletion of
   throwaway greeting messages ("hi", "hello", "hey", ...) to keep a group
   clean. Admins / whitelisted / approved users are exempt.

All three features are real, database-backed and persisted across restarts.
"""

import logging

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import Base, db
from utils import is_admin_command, is_group_command

logger = logging.getLogger(__name__)


class ContractAddress(Base):
    __tablename__ = "contract_addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    network = Column(String(64))
    address = Column(String(255))
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


class KeywordLink(Base):
    __tablename__ = "keyword_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    keyword = Column(String(64))
    text = Column(Text)
    url = Column(String(255))
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


class GreetingFilter(Base):
    __tablename__ = "greeting_filters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


def update_quick_replies_database():
    Base.metadata.create_all(bind=db.engine)


# Greetings that are auto-deleted when the filter is enabled. Matching is done
# on the whole (normalized) message, so "hi" is deleted but "this is hi" is not.
GREETINGS = {
    "hi",
    "hello",
    "hey",
    "heya",
    "heyy",
    "hola",
    "yo",
    "sup",
    "howdy",
    "hi there",
    "hello there",
    "hey there",
    "good morning",
    "good afternoon",
    "good evening",
    "gm",
    "gn",
    "gd morning",
    "gd evening",
}

# Words that trigger the contract-address reply. Case-insensitive.
_CA_TRIGGERS = {"ca", "contract", "contracts", "contract address", "contract addresses"}


def _normalize(text: str) -> str:
    """Lower-case and strip punctuation/padding so greetings match cleanly."""
    return (text or "").strip().lower().strip("!?.,;: ~")


def _is_greeting(text: str) -> bool:
    return _normalize(text) in GREETINGS


def get_contract_addresses(chat_id: int):
    """Return (network, address) rows for a chat, newest first."""
    session = db.get_session()
    try:
        rows = (
            session.query(ContractAddress)
            .filter(ContractAddress.chat_id == chat_id)
            .order_by(ContractAddress.created_at.asc())
            .all()
        )
        return [(r.network, r.address) for r in rows]
    finally:
        session.close()


def get_keyword_links(chat_id: int):
    """Return (keyword, text, url) rows sorted by keyword length (specific first)."""
    session = db.get_session()
    try:
        rows = session.query(KeywordLink).filter(KeywordLink.chat_id == chat_id).all()
        # Most-specific keyword first so "website" wins over "web".
        rows = sorted(rows, key=lambda r: len(r.keyword), reverse=True)
        return [(r.keyword, r.text, r.url) for r in rows]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@is_admin_command
@is_group_command
async def setcontract_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add or update a contract address. Usage: /setcontract <network> <address>."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/setcontract <network> <address>`\n"
            "Example: `/setcontract Arbitrum 0x1234...`\n\n"
            "When members type `ca` the bot replies with every configured\n"
            "contract address and its network.",
            parse_mode="Markdown",
        )
        return

    network = context.args[0].strip()
    address = context.args[1].strip()
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        existing = (
            session.query(ContractAddress)
            .filter(
                ContractAddress.chat_id == chat_id,
                ContractAddress.network == network.lower(),
            )
            .first()
        )
        if existing:
            existing.network = network
            existing.address = address
            session.commit()
            await update.message.reply_text(
                f"✅ Updated contract address for network **{network}**.",
                parse_mode="Markdown",
            )
        else:
            session.add(
                ContractAddress(
                    chat_id=chat_id,
                    network=network,
                    address=address,
                    created_by=update.effective_user.id,
                )
            )
            session.commit()
            await update.message.reply_text(
                f"✅ Added contract address for **{network}**.",
                parse_mode="Markdown",
            )
    finally:
        session.close()


@is_admin_command
@is_group_command
async def delcontract_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a contract address by network name. Usage: /delcontract <network>."""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/delcontract <network>`",
            parse_mode="Markdown",
        )
        return

    network = context.args[0].strip()
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        row = (
            session.query(ContractAddress)
            .filter(
                ContractAddress.chat_id == chat_id,
                ContractAddress.network == network.lower(),
            )
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            await update.message.reply_text(
                f"✅ Removed contract address for **{network}**.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"❌ No contract address found for network '{network}'.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def contracts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all configured contract addresses."""
    chat_id = update.effective_chat.id
    rows = get_contract_addresses(chat_id)
    if not rows:
        await update.message.reply_text(
            "📋 No contract addresses configured.\nUse `/setcontract <network> <address>` to add one."
        )
        return

    lines = ["📋 **Contract Addresses:**", ""]
    for network, address in rows:
        lines.append(f"• **{network}:** `{address}`")
    lines.append("")
    lines.append("Members can see these by typing `ca`.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@is_admin_command
@is_group_command
async def setkeywordlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a keyword -> link auto-reply. Usage: /setkeywordlink <keyword> <url> [text]."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/setkeywordlink <keyword> <url> [text]`\n"
            "Example: `/setkeywordlink website https://example.com Visit us!`\n\n"
            "When a member's message contains the keyword, the bot replies with\n"
            "the link as an inline button. Examples: `website`, `contact`, `proposal`.",
            parse_mode="Markdown",
        )
        return

    keyword = context.args[0].lower().strip()
    url = context.args[1].strip()
    text = " ".join(context.args[2:]).strip() if len(context.args) > 2 else keyword.capitalize()
    chat_id = update.effective_chat.id

    if not url.startswith(("http://", "https://", "t.me/")):
        await update.message.reply_text("❌ Please provide a valid URL starting with http://, https:// or t.me/.")
        return

    session = db.get_session()
    try:
        existing = (
            session.query(KeywordLink)
            .filter(
                KeywordLink.chat_id == chat_id,
                KeywordLink.keyword == keyword,
            )
            .first()
        )
        if existing:
            existing.url = url
            existing.text = text
            session.commit()
            await update.message.reply_text(
                f"✅ Updated keyword **{keyword}** → {url}.",
                parse_mode="Markdown",
            )
        else:
            session.add(
                KeywordLink(
                    chat_id=chat_id,
                    keyword=keyword,
                    url=url,
                    text=text,
                    created_by=update.effective_user.id,
                )
            )
            session.commit()
            await update.message.reply_text(
                f"✅ Keyword **{keyword}** now replies with: {url}.",
                parse_mode="Markdown",
            )
    finally:
        session.close()


@is_admin_command
@is_group_command
async def delkeywordlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a keyword link. Usage: /delkeywordlink <keyword>."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/delkeywordlink <keyword>`", parse_mode="Markdown")
        return

    keyword = context.args[0].lower().strip()
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        row = (
            session.query(KeywordLink)
            .filter(
                KeywordLink.chat_id == chat_id,
                KeywordLink.keyword == keyword,
            )
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            await update.message.reply_text(f"✅ Removed keyword **{keyword}**.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ No keyword '{keyword}' found.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def keywordlinks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all configured keyword links."""
    chat_id = update.effective_chat.id
    rows = get_keyword_links(chat_id)
    if not rows:
        await update.message.reply_text(
            "📋 No keyword links configured.\nUse `/setkeywordlink <keyword> <url> [text]` to add one."
        )
        return

    lines = ["📋 **Keyword Links:**", ""]
    for keyword, text, url in rows:
        lines.append(f"• **{keyword}** → {url}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@is_admin_command
@is_group_command
async def greetingfilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure greeting auto-delete. Usage: /greetingfilter on|off|status."""
    chat_id = update.effective_chat.id

    if not context.args or context.args[0].lower() == "status":
        session = db.get_session()
        try:
            row = session.query(GreetingFilter).filter(GreetingFilter.chat_id == chat_id).first()
            enabled = bool(row and row.enabled)
        finally:
            session.close()
        await update.message.reply_text(
            f"🧹 **Greeting Auto-Delete:** {'✅ Enabled' if enabled else '❌ Disabled'}\n\n"
            "When enabled, throwaway greetings (hi, hello, hey, ...) are deleted.\n"
            "Admins, whitelisted and approved users are exempt.\n\n"
            "• `/greetingfilter on` — enable\n"
            "• `/greetingfilter off` — disable",
            parse_mode="Markdown",
        )
        return

    sub = context.args[0].lower()
    if sub not in ("on", "off", "enable", "disable"):
        await update.message.reply_text("❌ Usage: `/greetingfilter on|off`", parse_mode="Markdown")
        return

    enabled = sub in ("on", "enable")
    session = db.get_session()
    try:
        row = session.query(GreetingFilter).filter(GreetingFilter.chat_id == chat_id).first()
        if row:
            row.enabled = enabled
        else:
            session.add(GreetingFilter(chat_id=chat_id, enabled=enabled))
        session.commit()
    finally:
        session.close()
    await update.message.reply_text(
        f"🧹 Greeting auto-delete {'enabled' if enabled else 'disabled'}.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Message processing (called from bot.handle_all_messages)
# ---------------------------------------------------------------------------


def _greeting_filter_enabled(chat_id: int) -> bool:
    session = db.get_session()
    try:
        row = session.query(GreetingFilter).filter(GreetingFilter.chat_id == chat_id).first()
        return bool(row and row.enabled)
    finally:
        session.close()


async def handle_quick_replies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Process a text message against quick-reply rules. Returns True if the bot
    handled (and possibly deleted) the message, so the caller can stop.
    """
    message = update.message
    if not message or not message.text or not update.effective_user:
        return False

    text = message.text.strip()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    is_exempt = db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id) or db.is_approved(user_id, chat_id)

    lowered = text.lower().strip("!?.,;: ")

    # 1) Contract address query (anyone may ask).
    if lowered in _CA_TRIGGERS:
        rows = get_contract_addresses(chat_id)
        if rows:
            lines = ["📜 **Contract Addresses:**", ""]
            for network, address in rows:
                lines.append(f"• **{network}:** `{address}`")
            await message.reply_text("\n".join(lines), parse_mode="Markdown")
            return True
        return False

    # 2) Keyword links (anyone may trigger).
    for keyword, link_text, url in get_keyword_links(chat_id):
        if keyword in lowered:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(link_text or keyword.capitalize(), url=url)]])
            await message.reply_text(link_text or f"🔗 **{keyword.capitalize()}**", reply_markup=keyboard)
            return True

    # 3) Greeting auto-delete (exempts admins/whitelisted/approved).
    if not is_exempt and _greeting_filter_enabled(chat_id) and _is_greeting(text):
        try:
            await context.bot.delete_message(chat_id, message.message_id)
            logger.info(f"Greeting filter: deleted greeting from {user_id} in {chat_id}")
        except Exception as e:
            logger.error(f"Greeting filter: failed to delete message in {chat_id}: {e}")
        return True

    return False


# Initialize tables
update_quick_replies_database()
