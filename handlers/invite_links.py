"""
Invite-link system — mirrors Rose's /link feature.

`/link` creates a unique, per-user Telegram invite link for the current group
(each user gets their own named link so joins can be attributed back to them).
`/link_stat` (alias `/linkstats`) shows the total number of joins on each of the
group's invite links, plus a per-user breakdown for admins.

Because Telegram's Bot API cannot directly report "how many people joined via a
specific invite link" after the fact, join attribution is done by listening to
``chat_member`` / "new chat member" updates and reading ``invite_link.name``,
which we set to a stable per-user token on creation. The database keeps two
things in sync:

* ``InviteLink`` — one row per link the bot has created, keyed by ``name`` (the
  unique token) so joins can be matched back to it.
* ``LinkJoin`` — one row per attributed join, so totals are queryable even
  though Telegram does not expose per-link member counts.
"""

import logging
import random

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from telegram import Update
from telegram.ext import ContextTypes

from database import Base, db
from utils import is_group_command

logger = logging.getLogger(__name__)


class InviteLink(Base):
    __tablename__ = "invite_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    name = Column(String(64), index=True)  # unique per-user token
    invite_link = Column(String(255))
    created_by = Column(BigInteger)  # user who requested the link
    created_at = Column(DateTime, default=func.now())


class LinkJoin(Base):
    __tablename__ = "link_joins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    invite_name = Column(String(64), index=True)  # matches InviteLink.name
    user_id = Column(BigInteger)  # the member who joined
    joined_at = Column(DateTime, default=func.now())


def update_invite_links_database():
    Base.metadata.create_all(bind=db.engine)


# 22 chars, unambiguous (no 0/O/1/l/I) so the token is easy to read back from
# Telegram's invite-link "name" field.
_TOKEN_ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TOKEN_LENGTH = 12


def _new_token() -> str:
    return "".join(random.choices(_TOKEN_ALPHABET, k=_TOKEN_LENGTH))


async def _get_telegram_admins(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Return the set of Telegram admin/owner user IDs, or None if unavailable."""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return {a.user.id for a in admins}
    except Exception as e:
        logger.warning(f"Could not fetch Telegram admins for {chat_id}: {e}")
        return None


@is_group_command
async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a unique invite link for the requesting user in this group."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    session = db.get_session()
    try:
        # Reuse an existing link for this user if we already created one.
        existing = (
            session.query(InviteLink)
            .filter(
                InviteLink.chat_id == chat_id,
                InviteLink.created_by == user.id,
            )
            .first()
        )
        if existing:
            await update.message.reply_text(
                f"🔗 **Your invite link for this group:**\n\n"
                f"{existing.invite_link}\n\n"
                f"Share it to invite new members. Joins are tracked under your link.\n"
                f"Check totals with `/link_stat`.",
                parse_mode="Markdown",
            )
            return

        token = _new_token()
        invite = await context.bot.create_chat_invite_link(
            chat_id=chat_id,
            name=token,
            creates_join_request=False,
        )
        invite_url = invite.invite_link

        session.add(
            InviteLink(
                chat_id=chat_id,
                name=token,
                invite_link=invite_url,
                created_by=user.id,
            )
        )
        session.commit()

        await update.message.reply_text(
            f"🔗 **Your unique invite link has been created:**\n\n"
            f"{invite_url}\n\n"
            f"Share it to invite new members. Joins are tracked under your link.\n"
            f"Check totals with `/link_stat`.",
            parse_mode="Markdown",
        )
    finally:
        session.close()


@is_group_command
async def link_stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total joins per invite link (per-user breakdown for admins)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # An admin (or the link owner) sees every link; a regular member only sees
    # their own links.
    admins = await _get_telegram_admins(context, chat_id)
    is_admin = admins is not None and user_id in admins

    session = db.get_session()
    try:
        links = session.query(InviteLink).filter(InviteLink.chat_id == chat_id).all()

        if not is_admin:
            links = [link for link in links if link.created_by == user_id]

        if not links:
            await update.message.reply_text(
                "🔗 No invite links yet.\nUse `/link` to create your own unique invite link."
            )
            return

        lines = ["🔗 **Invite Link Statistics:**", ""]
        total_joins = 0
        for link in links:
            count = (
                session.query(LinkJoin)
                .filter(
                    LinkJoin.chat_id == chat_id,
                    LinkJoin.invite_name == link.name,
                )
                .count()
            )
            total_joins += count
            lines.append(f"• `{link.invite_link}` — **{count}** join(s)")
            if is_admin:
                lines.append(f"    _created by {link.created_by}_")

        lines.append("")
        lines.append(f"**Total joins via invite links:** {total_joins}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        session.close()


# Called from `handle_chat_member_update` (in events.py) whenever someone joins
# via an invite link, so we can attribute the join to the link's owner.
def record_join_from_chat_member(chat_id: int, user_id: int, invite_name: str):
    if not invite_name:
        return
    session = db.get_session()
    try:
        session.add(LinkJoin(chat_id=chat_id, invite_name=invite_name, user_id=user_id))
        session.commit()
    finally:
        session.close()


# Initialize table
update_invite_links_database()
