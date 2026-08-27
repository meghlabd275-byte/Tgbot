"""
Approvals module — mirrors Rose's /approve system.

Approved users are immune to ALL automated actions (anti-flood, block/filters,
locks, URL remover) while remaining non-admins. This is useful for trusted
members you don't want to promote to admin but who shouldn't be moderated
by the bot.

Also provides an "ignored users" list: users the bot will entirely ignore
(no automated action ever applies to them).
"""
import logging

from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func

from telegram import Update
from telegram.ext import ContextTypes

from database import Base, db
from utils import (
    is_admin_command, is_group_command, is_owner_command,
    get_user_from_message, format_user_mention,
)

logger = logging.getLogger(__name__)


class Approved(Base):
    __tablename__ = 'approved_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    user_id = Column(BigInteger)
    reason = Column(Text)
    approved_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


class Ignored(Base):
    __tablename__ = 'ignored_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    user_id = Column(BigInteger)
    ignored_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


def update_approvals_database():
    Base.metadata.create_all(bind=db.engine)


def is_approved(user_id: int, chat_id: int) -> bool:
    session = db.get_session()
    try:
        return session.query(Approved).filter(
            Approved.chat_id == chat_id,
            Approved.user_id == user_id
        ).first() is not None
    finally:
        session.close()


def is_ignored(user_id: int, chat_id: int) -> bool:
    session = db.get_session()
    try:
        return session.query(Ignored).filter(
            Ignored.chat_id == chat_id,
            Ignored.user_id == user_id
        ).first() is not None
    finally:
        session.close()


def _resolve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resolve a target user from reply/args and return (user_id, user_obj_or_None)."""
    info = get_user_from_message(update, context)
    if not info:
        return None
    user_id, user_obj = info
    if user_id is None:
        return None
    return user_id, user_obj


@is_admin_command
@is_group_command
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user (exempt from all automated actions)."""
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Usage: `/approve <id/@username/reply> [reason]`\n"
            "Approved users are exempt from filters, locks, anti-flood and URL removal.",
            parse_mode='Markdown',
        )
        return

    target = _resolve_user(update, context)
    if not target:
        await update.message.reply_text("❌ Could not identify the user. Reply to their message or pass an ID.")
        return

    target_id, _user_obj = target
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if target_id and context.args and len(context.args) > 1 else None

    session = db.get_session()
    try:
        existing = session.query(Approved).filter(
            Approved.chat_id == chat_id,
            Approved.user_id == target_id
        ).first()
        if existing:
            existing.reason = reason or existing.reason
            session.commit()
            await update.message.reply_text("ℹ️ This user is already approved; updated their approval reason.")
        else:
            session.add(Approved(
                chat_id=chat_id,
                user_id=target_id,
                reason=reason,
                approved_by=admin_id,
            ))
            session.commit()
            await update.message.reply_text(
                f"✅ User `{target_id}` is now approved. They are exempt from automated actions in this chat.",
                parse_mode='Markdown',
            )
    finally:
        session.close()


@is_admin_command
@is_group_command
async def unapprove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user's approval."""
    target = _resolve_user(update, context)
    if not target:
        await update.message.reply_text("❌ Could not identify the user.")
        return

    target_id, _user_obj = target
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        row = session.query(Approved).filter(
            Approved.chat_id == chat_id,
            Approved.user_id == target_id
        ).first()
        if row:
            session.delete(row)
            session.commit()
            await update.message.reply_text(f"✅ User `{target_id}` is no longer approved.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ This user is not approved.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def approval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check a user's approval status."""
    target = _resolve_user(update, context)
    if not target:
        await update.message.reply_text("❌ Could not identify the user.")
        return

    target_id, user_obj = target
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        row = session.query(Approved).filter(
            Approved.chat_id == chat_id,
            Approved.user_id == target_id
        ).first()
        mention = format_user_mention(user_obj) if user_obj else f"User `{target_id}`"
        if row:
            msg = f"✅ {mention} is approved.\n"
            if row.reason:
                msg += f"**Reason:** {row.reason}\n"
            msg += f"**Approved by:** `{row.approved_by}`\n"
            msg += f"**Since:** {row.created_at.strftime('%Y-%m-%d %H:%M')}"
            await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ {mention} is not approved.", parse_mode='Markdown')
    finally:
        session.close()


@is_admin_command
@is_group_command
async def approved_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all approved users."""
    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        rows = session.query(Approved).filter(Approved.chat_id == chat_id).order_by(Approved.created_at.desc()).limit(50).all()
        if not rows:
            await update.message.reply_text("📋 No approved users in this chat.")
            return
        msg = "📋 **Approved Users:**\n\n"
        for r in rows:
            msg += f"• `{r.user_id}`"
            if r.reason:
                msg += f" — {r.reason}"
            msg += "\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    finally:
        session.close()


@is_owner_command
@is_group_command
async def unapproveall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove ALL approvals (owner only)."""
    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        count = session.query(Approved).filter(Approved.chat_id == chat_id).delete()
        session.commit()
        await update.message.reply_text(f"✅ Removed {count} approved user(s).")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def ignore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Make the bot ignore a user entirely in this chat."""
    target = _resolve_user(update, context)
    if not target:
        await update.message.reply_text("❌ Could not identify the user.")
        return

    target_id, _user_obj = target
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id

    session = db.get_session()
    try:
        existing = session.query(Ignored).filter(
            Ignored.chat_id == chat_id,
            Ignored.user_id == target_id
        ).first()
        if existing:
            await update.message.reply_text("ℹ️ This user is already ignored.")
        else:
            session.add(Ignored(chat_id=chat_id, user_id=target_id, ignored_by=admin_id))
            session.commit()
            await update.message.reply_text(f"✅ The bot will now ignore user `{target_id}`.", parse_mode='Markdown')
    finally:
        session.close()


@is_admin_command
@is_group_command
async def unignore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop ignoring a user."""
    target = _resolve_user(update, context)
    if not target:
        await update.message.reply_text("❌ Could not identify the user.")
        return

    target_id, _user_obj = target
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        row = session.query(Ignored).filter(
            Ignored.chat_id == chat_id,
            Ignored.user_id == target_id
        ).first()
        if row:
            session.delete(row)
            session.commit()
            await update.message.reply_text(f"✅ No longer ignoring user `{target_id}`.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ This user is not being ignored.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def ignored_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all ignored users."""
    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        rows = session.query(Ignored).filter(Ignored.chat_id == chat_id).order_by(Ignored.created_at.desc()).limit(50).all()
        if not rows:
            await update.message.reply_text("📋 No ignored users in this chat.")
            return
        msg = "📋 **Ignored Users:**\n\n"
        for r in rows:
            msg += f"• `{r.user_id}`\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    finally:
        session.close()


# Initialize table
update_approvals_database()
