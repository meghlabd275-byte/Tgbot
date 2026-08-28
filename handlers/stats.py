"""
Chat statistics — member activity tracking, leaderboards, and admin stats.

* ``/stats`` (or ``/statistics``) — show total/top active members, admin count,
  ban/warn/mute counts, and other useful group stats.
* ``/top`` (or ``/leaderboard``) — show the top-10 most active members by message
  count in the current chat.

Message counts are tracked persistently in the ``message_counts`` table so
activity survives bot restarts. The ``handle_message`` event in ``events.py``
increments the counter for every non-command text message in a registered chat.
"""

import logging

from sqlalchemy import BigInteger, Column, DateTime, Integer, UniqueConstraint
from sqlalchemy.sql import func
from telegram import Update
from telegram.ext import ContextTypes

from database import Base, db

logger = logging.getLogger(__name__)


class MessageCount(Base):
    __tablename__ = "message_counts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    user_id = Column(BigInteger, index=True)
    count = Column(Integer, default=1)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_message_counts_chat_user"),)


def update_stats_database():
    Base.metadata.create_all(bind=db.engine)


def increment_message_count(chat_id: int, user_id: int):
    """Increment the message counter for a user in a chat. Called from
    ``handle_message`` in ``events.py`` for every non-command text message."""
    session = db.get_session()
    try:
        row = (
            session.query(MessageCount)
            .filter(
                MessageCount.chat_id == chat_id,
                MessageCount.user_id == user_id,
            )
            .first()
        )
        if row:
            # `updated_at` is refreshed automatically via onupdate=func.now().
            row.count = (row.count or 0) + 1
        else:
            session.add(MessageCount(chat_id=chat_id, user_id=user_id, count=1))
        session.commit()
    finally:
        session.close()


def get_top_members(chat_id: int, limit: int = 10):
    """Return the top-N members by message count in a chat."""
    session = db.get_session()
    try:
        rows = (
            session.query(MessageCount)
            .filter(MessageCount.chat_id == chat_id)
            .order_by(MessageCount.count.desc())
            .limit(limit)
            .all()
        )
        return [(r.user_id, r.count) for r in rows]
    finally:
        session.close()


def get_chat_stats(chat_id: int):
    """Return aggregate statistics for a chat as a dict."""
    session = db.get_session()
    try:
        # Total active members (users who have sent at least one message)
        active_members = session.query(MessageCount).filter(MessageCount.chat_id == chat_id).count()

        # Total messages tracked
        total_messages = (
            session.query(func.sum(MessageCount.count)).filter(MessageCount.chat_id == chat_id).scalar() or 0
        )

        # Admin count (from bot's admin DB)
        admin_count = session.query(db.Admin).filter(db.Admin.chat_id == chat_id).count()

        # Ban count
        ban_count = session.query(db.Ban).filter((db.Ban.chat_id == chat_id) | (db.Ban.is_global == True)).count()

        # Warn count
        warn_count = (
            session.query(db.Warning).filter((db.Warning.chat_id == chat_id) | (db.Warning.is_global == True)).count()
        )

        # Mute count
        mute_count = session.query(db.Mute).filter(db.Mute.chat_id == chat_id).count()

        # Whitelist count
        whitelist_count = (
            session.query(db.Whitelist)
            .filter((db.Whitelist.chat_id == chat_id) | (db.Whitelist.is_global == True))
            .count()
        )

        return {
            "active_members": active_members,
            "total_messages": total_messages,
            "admin_count": admin_count,
            "ban_count": ban_count,
            "warn_count": warn_count,
            "mute_count": mute_count,
            "whitelist_count": whitelist_count,
        }
    finally:
        session.close()


def _resolve_usernames(user_ids):
    """Map a list of user_ids to display names (username or full name)."""
    if not user_ids:
        return {}
    session = db.get_session()
    try:
        rows = session.query(db.User).filter(db.User.id.in_(user_ids)).all()
        out = {}
        for u in rows:
            if u.username:
                out[u.id] = f"@{u.username}"
            else:
                name = (u.first_name or "").strip()
                if u.last_name:
                    name = f"{name} {u.last_name}".strip()
                out[u.id] = name or f"`{u.id}`"
        return out
    finally:
        session.close()


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chat statistics — total/top active members, admin counts, bans, etc."""
    chat_id = update.effective_chat.id

    try:
        member_count = await context.bot.get_chat_member_count(chat_id)
    except Exception:
        member_count = "Unknown"

    s = get_chat_stats(chat_id)
    top = get_top_members(chat_id, limit=5)

    lines = [
        "📊 **Chat Statistics**",
        "",
        f"**Total Members:** {member_count}",
        f"**Active Members (tracked):** {s['active_members']}",
        f"**Total Messages (tracked):** {s['total_messages']}",
        f"**Registered Admins:** {s['admin_count']}",
        f"**Banned Users:** {s['ban_count']}",
        f"**Total Warnings:** {s['warn_count']}",
        f"**Active Mutes:** {s['mute_count']}",
        f"**Whitelisted Users:** {s['whitelist_count']}",
    ]

    if top:
        names = _resolve_usernames([uid for uid, _ in top])
        lines.append("")
        lines.append("🏆 **Top 5 Most Active Members:**")
        for rank, (uid, cnt) in enumerate(top, 1):
            mention = names.get(uid, f"`{uid}`")
            lines.append(f"{rank}. {mention} — {cnt} messages")

    lines.append("")
    lines.append("Use `/top` to see the full leaderboard.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the top-15 most active members by message count."""
    chat_id = update.effective_chat.id
    top = get_top_members(chat_id, limit=15)

    if not top:
        await update.message.reply_text("🏆 No message activity data yet. Start chatting and I'll track it!")
        return

    names = _resolve_usernames([uid for uid, _ in top])
    lines = ["🏆 **Top Active Members:**", ""]
    for rank, (uid, cnt) in enumerate(top, 1):
        mention = names.get(uid, f"`{uid}`")
        lines.append(f"{rank}. {mention} — {cnt} messages")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


update_stats_database()
