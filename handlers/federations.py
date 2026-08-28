"""
Federations module — mirrors Rose's federation system.

A federation is a shared ban list with its own owner and admins. Any chat can
be "joined" to a federation; once joined, bans recorded in the federation are
automatically enforced in every connected chat.

Commands:
  /fednew <name>                 create a new federation
  /feddel                        delete your federation (owner only)
  /fedrename <name>              rename your federation
  /fedinfo                       show info about the current federation
  /fedadmins                     list federation admins
  /fedpromote <id>               promote a federation admin
  /feddemote <id>                demote a federation admin
  /fedjoin <fed_id>              join your chat to a federation
  /fedleave                      leave the current federation
  /fedchat                       show the federation this chat belongs to
  /fedban <user> [reason]        ban globally within the federation
  /fedunban <user>               unban from the federation
  /fedkick <user>                kick from all federation chats
  /fedmute <user> <time>         mute across federation chats
  /fedbans                       list federation bans
"""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from database import Base, db
from utils import (
    format_time_duration,
    format_user_mention,
    get_user_from_message,
    is_admin_command,
    is_group_command,
    parse_time_string,
)

logger = logging.getLogger(__name__)


class Federation(Base):
    __tablename__ = "federations"

    id = Column(String(36), primary_key=True)
    name = Column(String(255))
    owner_id = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


class FederationAdmin(Base):
    __tablename__ = "federation_admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    user_id = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())


class FederationChat(Base):
    __tablename__ = "federation_chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    chat_id = Column(BigInteger, unique=True)
    joined_by = Column(BigInteger)
    joined_at = Column(DateTime, default=func.now())


class FederationBan(Base):
    __tablename__ = "federation_bans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    user_id = Column(BigInteger)
    banned_by = Column(BigInteger)
    reason = Column(Text)
    created_at = Column(DateTime, default=func.now())


class FederationMute(Base):
    __tablename__ = "federation_mutes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fed_id = Column(String(36))
    user_id = Column(BigInteger)
    muted_by = Column(BigInteger)
    until = Column(DateTime)
    reason = Column(Text)
    created_at = Column(DateTime, default=func.now())


def update_federations_database():
    Base.metadata.create_all(bind=db.engine)


# ---------------------------------------------------------------------------
# Federation helpers
# ---------------------------------------------------------------------------


def get_federation_by_owner(owner_id: int):
    session = db.get_session()
    try:
        return session.query(Federation).filter(Federation.owner_id == owner_id).first()
    finally:
        session.close()


def get_federation_for_chat(chat_id: int):
    session = db.get_session()
    try:
        link = session.query(FederationChat).filter(FederationChat.chat_id == chat_id).first()
        if not link:
            return None
        return session.query(Federation).filter(Federation.id == link.fed_id).first()
    finally:
        session.close()


def get_chat_fed_id(chat_id: int):
    session = db.get_session()
    try:
        link = session.query(FederationChat).filter(FederationChat.chat_id == chat_id).first()
        return link.fed_id if link else None
    finally:
        session.close()


def is_fed_admin(fed_id: str, user_id: int) -> bool:
    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.id == fed_id).first()
        if fed and fed.owner_id == user_id:
            return True
        return (
            session.query(FederationAdmin)
            .filter(FederationAdmin.fed_id == fed_id, FederationAdmin.user_id == user_id)
            .first()
            is not None
        )
    finally:
        session.close()


def is_user_fed_banned(fed_id: str, user_id: int) -> bool:
    session = db.get_session()
    try:
        return (
            session.query(FederationBan)
            .filter(FederationBan.fed_id == fed_id, FederationBan.user_id == user_id)
            .first()
            is not None
        )
    finally:
        session.close()


def get_fed_chat_ids(fed_id: str):
    session = db.get_session()
    try:
        links = session.query(FederationChat).filter(FederationChat.fed_id == fed_id).all()
        return [link.chat_id for link in links]
    finally:
        session.close()


def get_user_fed_bans(user_id: int):
    """Return all FederationBan rows affecting a user (for chat enforcement)."""
    session = db.get_session()
    try:
        return session.query(FederationBan).filter(FederationBan.user_id == user_id).all()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def fednew_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new federation owned by the caller."""
    user_id = update.effective_user.id
    name = " ".join(context.args) if context.args else "My Federation"

    session = db.get_session()
    try:
        existing = session.query(Federation).filter(Federation.owner_id == user_id).first()
        if existing:
            await update.message.reply_text("❌ You already own a federation. You can only own one.")
            return

        fed_id = uuid.uuid4().hex
        session.add(Federation(id=fed_id, name=name, owner_id=user_id))
        session.commit()
        await update.message.reply_text(
            f"✅ Federation **{name}** created!\n\n"
            f"**Federation ID:** `{fed_id}`\n\n"
            f"Use `/fedjoin {fed_id}` in your group to join it, or `/fedban` "
            f"and `/fedpromote` to manage it.",
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def feddel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the federation you own (owner only)."""
    user_id = update.effective_user.id

    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.owner_id == user_id).first()
        if not fed:
            await update.message.reply_text("❌ You don't own a federation.")
            return
        session.query(FederationBan).filter(FederationBan.fed_id == fed.id).delete()
        session.query(FederationMute).filter(FederationMute.fed_id == fed.id).delete()
        session.query(FederationChat).filter(FederationChat.fed_id == fed.id).delete()
        session.query(FederationAdmin).filter(FederationAdmin.fed_id == fed.id).delete()
        session.delete(fed)
        session.commit()
        await update.message.reply_text("✅ Federation deleted.")
    finally:
        session.close()


async def fedrename_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rename the federation you own."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❌ Usage: `/fedrename <new name>`", parse_mode="Markdown")
        return
    name = " ".join(context.args)

    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.owner_id == user_id).first()
        if not fed:
            await update.message.reply_text("❌ You don't own a federation.")
            return
        fed.name = name
        session.commit()
        await update.message.reply_text(f"✅ Federation renamed to **{name}**.", parse_mode="Markdown")
    finally:
        session.close()


async def fedinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show info about the current federation (owner or context-based)."""
    session = db.get_session()
    try:
        chat_id = update.effective_chat.id
        fed = get_federation_for_chat(chat_id)
        if not fed:
            fed = session.query(Federation).filter(Federation.owner_id == update.effective_user.id).first()
        if not fed:
            await update.message.reply_text("❌ No federation found. Create one with `/fednew`.")
            return

        admin_count = session.query(FederationAdmin).filter(FederationAdmin.fed_id == fed.id).count()
        ban_count = session.query(FederationBan).filter(FederationBan.fed_id == fed.id).count()
        chat_count = session.query(FederationChat).filter(FederationChat.fed_id == fed.id).count()

        msg = (
            f"🏰 **{fed.name}**\n\n"
            f"**Federation ID:** `{fed.id}`\n"
            f"**Owner:** `{fed.owner_id}`\n"
            f"**Admins:** {admin_count}\n"
            f"**Bans:** {ban_count}\n"
            f"**Connected chats:** {chat_count}\n"
            f"**Created:** {fed.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        session.close()


async def fedadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = db.get_session()
    try:
        fed = get_federation_for_chat(update.effective_chat.id)
        if not fed:
            fed = session.query(Federation).filter(Federation.owner_id == update.effective_user.id).first()
        if not fed:
            await update.message.reply_text("❌ No federation found.")
            return
        admins = session.query(FederationAdmin).filter(FederationAdmin.fed_id == fed.id).all()
        msg = f"👥 **Federation Admins for {fed.name}**\n\n"
        msg += f"👑 Owner: `{fed.owner_id}`\n"
        for a in admins:
            msg += f"• `{a.user_id}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        session.close()


async def fedpromote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Specify a user to promote.")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return

    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.owner_id == user_id).first()
        if not fed:
            await update.message.reply_text("❌ You don't own a federation.")
            return
        exists = (
            session.query(FederationAdmin)
            .filter(FederationAdmin.fed_id == fed.id, FederationAdmin.user_id == target_id)
            .first()
        )
        if not exists:
            session.add(FederationAdmin(fed_id=fed.id, user_id=target_id))
            session.commit()
        mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
        await update.message.reply_text(f"✅ {mention} is now a federation admin.", parse_mode="Markdown")
    finally:
        session.close()


async def feddemote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Specify a user to demote.")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return

    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.owner_id == user_id).first()
        if not fed:
            await update.message.reply_text("❌ You don't own a federation.")
            return
        row = (
            session.query(FederationAdmin)
            .filter(FederationAdmin.fed_id == fed.id, FederationAdmin.user_id == target_id)
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
            await update.message.reply_text(f"✅ {mention} removed from federation admins.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ That user is not a federation admin.")
    finally:
        session.close()


@is_admin_command
@is_group_command
async def fedjoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/fedjoin <federation_id>`", parse_mode="Markdown")
        return
    fed_id = context.args[0]
    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        fed = session.query(Federation).filter(Federation.id == fed_id).first()
        if not fed:
            await update.message.reply_text("❌ Federation not found.")
            return

        existing = session.query(FederationChat).filter(FederationChat.chat_id == chat_id).first()
        if existing:
            if existing.fed_id == fed_id:
                await update.message.reply_text("ℹ️ This chat is already in that federation.")
            else:
                await update.message.reply_text("❌ This chat is already in another federation. Use `/fedleave` first.")
            return

        session.add(FederationChat(fed_id=fed_id, chat_id=chat_id, joined_by=update.effective_user.id))
        session.commit()
        await update.message.reply_text(
            f"✅ This chat has joined federation **{fed.name}**.\nFederation bans will now be enforced in this chat.",
            parse_mode="Markdown",
        )
    finally:
        session.close()


@is_admin_command
@is_group_command
async def fedleave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        link = session.query(FederationChat).filter(FederationChat.chat_id == chat_id).first()
        if link:
            session.delete(link)
            session.commit()
            await update.message.reply_text("✅ This chat has left its federation.")
        else:
            await update.message.reply_text("❌ This chat is not in any federation.")
    finally:
        session.close()


async def fedchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    fed = get_federation_for_chat(chat_id)
    if not fed:
        await update.message.reply_text("❌ This chat is not in any federation.")
        return
    await update.message.reply_text(
        f"🏰 This chat belongs to federation **{fed.name}** (`{fed.id}`).",
        parse_mode="Markdown",
    )


def _resolve_fed_for_action(session, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Determine the federation an action should target. In a group, use the
    group's federation; in private, fall back to the owner's federation.
    Returns the fed object or None.
    """
    chat = update.effective_chat
    if chat.type == "private":
        return session.query(Federation).filter(Federation.owner_id == update.effective_user.id).first()
    return get_federation_for_chat(chat.id)


async def fedban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Usage: `/fedban <id/reply> [reason]`", parse_mode="Markdown")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"
    actor = update.effective_user.id

    session = db.get_session()
    try:
        fed = _resolve_fed_for_action(session, update, context)
        if not fed:
            await update.message.reply_text(
                "❌ No federation found. Join one with `/fedjoin` or create one with `/fednew`."
            )
            return
        if not is_fed_admin(fed.id, actor):
            await update.message.reply_text("❌ You must be a federation admin to ban in it.")
            return

        if is_user_fed_banned(fed.id, target_id):
            await update.message.reply_text("ℹ️ That user is already federated-banned.")
            return

        session.add(FederationBan(fed_id=fed.id, user_id=target_id, banned_by=actor, reason=reason))
        session.commit()

        # Enforce in all connected chats
        banned_chats = 0
        for cid in get_fed_chat_ids(fed.id):
            try:
                await context.bot.ban_chat_member(cid, target_id)
                banned_chats += 1
            except Exception:
                pass

        mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
        await update.message.reply_text(
            f"🏰 {mention} has been banned in federation **{fed.name}**!\n"
            f"**Reason:** {reason}\n"
            f"**Applied in {banned_chats} chat(s)**",
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def fedunban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Usage: `/fedunban <id/reply>`", parse_mode="Markdown")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return
    actor = update.effective_user.id

    session = db.get_session()
    try:
        fed = _resolve_fed_for_action(session, update, context)
        if not fed:
            await update.message.reply_text("❌ No federation found.")
            return
        if not is_fed_admin(fed.id, actor):
            await update.message.reply_text("❌ You must be a federation admin to unban.")
            return

        row = (
            session.query(FederationBan)
            .filter(FederationBan.fed_id == fed.id, FederationBan.user_id == target_id)
            .first()
        )
        if not row:
            await update.message.reply_text("❌ That user is not federated-banned.")
            return
        session.delete(row)
        session.commit()

        unbanned = 0
        for cid in get_fed_chat_ids(fed.id):
            try:
                await context.bot.unban_chat_member(cid, target_id)
                unbanned += 1
            except Exception:
                pass

        mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
        await update.message.reply_text(
            f"✅ {mention} unbanned from federation **{fed.name}** ({unbanned} chats).",
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def fedkick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Usage: `/fedkick <id/reply>`", parse_mode="Markdown")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return
    actor = update.effective_user.id

    session = db.get_session()
    try:
        fed = _resolve_fed_for_action(session, update, context)
        if not fed:
            await update.message.reply_text("❌ No federation found.")
            return
        if not is_fed_admin(fed.id, actor):
            await update.message.reply_text("❌ You must be a federation admin to kick.")
            return

        kicked = 0
        for cid in get_fed_chat_ids(fed.id):
            try:
                await context.bot.ban_chat_member(cid, target_id)
                await context.bot.unban_chat_member(cid, target_id)
                kicked += 1
            except Exception:
                pass

        mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
        await update.message.reply_text(
            f"👢 {mention} kicked from federation **{fed.name}** ({kicked} chats).",
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def fedmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_user_from_message(update, context)
    if not info:
        await update.message.reply_text("❌ Usage: `/fedmute <id/reply> <time>`", parse_mode="Markdown")
        return
    target_id, target_obj = info
    if not target_id:
        await update.message.reply_text("❌ Please pass a numeric user ID.")
        return
    actor = update.effective_user.id

    # Determine duration: the first argument that is not the user id.
    # e.g. "/fedmute 1234 30m" -> 30 minutes; "/fedmute 1234" -> 1 hour.
    duration = 3600
    if context.args and len(context.args) >= 2:
        duration = parse_time_string(context.args[1])

    session = db.get_session()
    try:
        fed = _resolve_fed_for_action(session, update, context)
        if not fed:
            await update.message.reply_text("❌ No federation found.")
            return
        if not is_fed_admin(fed.id, actor):
            await update.message.reply_text("❌ You must be a federation admin to mute.")
            return

        until = datetime.now() + timedelta(seconds=duration)
        session.add(FederationMute(fed_id=fed.id, user_id=target_id, muted_by=actor, until=until))
        session.commit()

        muted = 0
        for cid in get_fed_chat_ids(fed.id):
            try:
                await context.bot.restrict_chat_member(
                    chat_id=cid,
                    user_id=target_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until,
                )
                muted += 1
            except Exception:
                pass

        mention = format_user_mention(target_obj) if target_obj else f"User `{target_id}`"
        await update.message.reply_text(
            f"🔇 {mention} muted for {format_time_duration(duration)} across federation **{fed.name}** ({muted} chats).",
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def fedbans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = db.get_session()
    try:
        fed = _resolve_fed_for_action(session, update, context)
        if not fed:
            await update.message.reply_text("❌ No federation found.")
            return
        bans = (
            session.query(FederationBan)
            .filter(FederationBan.fed_id == fed.id)
            .order_by(FederationBan.created_at.desc())
            .limit(50)
            .all()
        )
        if not bans:
            await update.message.reply_text("📋 No federation bans.")
            return
        msg = f"📋 **Federation Bans for {fed.name}:**\n\n"
        for b in bans:
            msg += f"• `{b.user_id}`"
            if b.reason:
                msg += f" — {b.reason}"
            msg += "\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Enforcement helper (called on new members joining a chat)
# ---------------------------------------------------------------------------


async def enforce_federation_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Called when new members join. If the chat is in a federation, ban any
    new member who is on the federation ban list.
    Returns True if any member was handled.
    """
    chat_id = update.effective_chat.id
    fed_id = get_chat_fed_id(chat_id)
    if not fed_id:
        return False

    new_members = update.message.new_chat_members or []
    handled = False
    session = db.get_session()
    try:
        for member in new_members:
            if member.is_bot:
                continue
            ban = (
                session.query(FederationBan)
                .filter(FederationBan.fed_id == fed_id, FederationBan.user_id == member.id)
                .first()
            )
            if ban:
                try:
                    await context.bot.ban_chat_member(chat_id, member.id)
                    handled = True
                    logger.info(f"Federation: banned {member.id} in {chat_id} (fed {fed_id})")
                except Exception as e:
                    logger.error(f"Federation: failed to ban {member.id}: {e}")
    finally:
        session.close()
    return handled


# Initialize table
update_federations_database()
