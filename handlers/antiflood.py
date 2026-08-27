from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from database import db, Base
from utils import (
    is_admin_command, is_group_command, parse_time_string, format_time_duration,
)
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Add persistent per-chat flood settings table
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime
from sqlalchemy.sql import func


class FloodSettings(Base):
    __tablename__ = 'flood_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    enabled = Column(Boolean, default=False)
    limit = Column(Integer, default=5)
    time_window = Column(Integer, default=10)  # seconds
    action = Column(String(20), default='mute')  # mute, kick, ban
    duration = Column(Integer, default=3600)  # mute duration in seconds
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class RaidSettings(Base):
    __tablename__ = 'raid_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    enabled = Column(Boolean, default=False)
    threshold = Column(Integer, default=10)   # joins within `window`
    window = Column(Integer, default=60)      # seconds
    duration = Column(Integer, default=300)   # seconds of under-attack mode
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def update_antiflood_database():
    Base.metadata.create_all(bind=db.engine)


# In-memory flood tracking (fast path for per-message checks)
_flood_tracker = defaultdict(lambda: deque())
# In-memory anti-raid join trackers
_raid_tracker = defaultdict(list)

FLOOD_DEFAULTS = {
    'enabled': False,
    'limit': 5,
    'time_window': 10,
    'action': 'mute',
    'duration': 3600,
}

RAID_DEFAULTS = {
    'enabled': False,
    'threshold': 10,
    'window': 60,
    'duration': 300,
}


def get_flood_settings(chat_id: int) -> dict:
    """Read persistent flood settings for a chat (falling back to defaults)."""
    session = db.get_session()
    try:
        row = session.query(FloodSettings).filter(FloodSettings.chat_id == chat_id).first()
        if not row:
            return dict(FLOOD_DEFAULTS)
        return {
            'enabled': row.enabled,
            'limit': row.limit,
            'time_window': row.time_window,
            'action': row.action,
            'duration': row.duration,
        }
    finally:
        session.close()


def set_flood_settings(chat_id: int, **kwargs):
    """Persist flood settings for a chat."""
    session = db.get_session()
    try:
        row = session.query(FloodSettings).filter(FloodSettings.chat_id == chat_id).first()
        if not row:
            row = FloodSettings(chat_id=chat_id, **kwargs)
            session.add(row)
        else:
            for k, v in kwargs.items():
                setattr(row, k, v)
        session.commit()
    finally:
        session.close()


def get_raid_settings(chat_id: int) -> dict:
    session = db.get_session()
    try:
        row = session.query(RaidSettings).filter(RaidSettings.chat_id == chat_id).first()
        if not row:
            return dict(RAID_DEFAULTS)
        return {
            'enabled': row.enabled,
            'threshold': row.threshold,
            'window': row.window,
            'duration': row.duration,
        }
    finally:
        session.close()


def set_raid_settings(chat_id: int, **kwargs):
    session = db.get_session()
    try:
        row = session.query(RaidSettings).filter(RaidSettings.chat_id == chat_id).first()
        if not row:
            row = RaidSettings(chat_id=chat_id, **kwargs)
            session.add(row)
        else:
            for k, v in kwargs.items():
                setattr(row, k, v)
        session.commit()
    finally:
        session.close()


class FloodControl:
    """Fast in-memory flood checker backed by persistent settings."""

    def __init__(self):
        self.user_messages = defaultdict(lambda: deque())

    def add_message(self, chat_id: int, user_id: int):
        now = datetime.now()
        settings = get_flood_settings(chat_id)
        if not settings['enabled']:
            return False

        cutoff = now - timedelta(seconds=settings['time_window'])
        user_key = f"{chat_id}:{user_id}"

        while self.user_messages[user_key] and self.user_messages[user_key][0] < cutoff:
            self.user_messages[user_key].popleft()

        self.user_messages[user_key].append(now)
        return len(self.user_messages[user_key]) > settings['limit']


# Global flood control instance
flood_control = FloodControl()


@is_admin_command
@is_group_command
async def setflood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set flood protection limit"""
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ Please provide a valid number.\n"
            "Usage: `/setflood 5` (allow 5 messages per 10 seconds)\n"
            "Use `/setflood 0` to disable flood protection.",
            parse_mode='Markdown'
        )
        return

    limit = int(context.args[0])
    chat_id = update.effective_chat.id

    if limit == 0:
        set_flood_settings(chat_id, enabled=False)
        await update.message.reply_text("✅ Flood protection has been disabled.")
    else:
        set_flood_settings(chat_id, enabled=True, limit=limit)
        settings = get_flood_settings(chat_id)
        await update.message.reply_text(
            f"✅ Flood protection set to {limit} messages per {settings['time_window']} seconds.\n"
            f"Action: {settings['action'].title()}"
        )


@is_admin_command
@is_group_command
async def setfloodmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set flood protection action"""
    if not context.args or context.args[0].lower() not in ['mute', 'kick', 'ban']:
        await update.message.reply_text(
            "❌ Please specify a valid action.\n"
            "Usage: `/setfloodmode mute|kick|ban`\n"
            "Available actions:\n"
            "• `mute` - Mute the user temporarily\n"
            "• `kick` - Kick the user from group\n"
            "• `ban` - Ban the user permanently",
            parse_mode='Markdown'
        )
        return

    action = context.args[0].lower()
    duration = 3600  # Default 1 hour for mute

    if action == 'mute' and len(context.args) > 1:
        duration = parse_time_string(context.args[1])

    chat_id = update.effective_chat.id
    set_flood_settings(chat_id, action=action, duration=duration)

    if action == 'mute':
        await update.message.reply_text(
            f"✅ Flood action set to **{action}** for {format_time_duration(duration)}.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"✅ Flood action set to **{action}**.",
            parse_mode='Markdown'
        )


@is_admin_command
@is_group_command
async def flood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current flood settings"""
    chat_id = update.effective_chat.id
    settings = get_flood_settings(chat_id)

    if not settings['enabled']:
        await update.message.reply_text("🌊 Flood protection is currently **disabled**.", parse_mode='Markdown')
        return

    flood_info = f"""🌊 **Flood Protection Settings**

**Status:** Enabled
**Limit:** {settings['limit']} messages per {settings['time_window']} seconds
**Action:** {settings['action'].title()}"""

    if settings['action'] == 'mute':
        flood_info += f"\n**Mute Duration:** {format_time_duration(settings['duration'])}"

    flood_info += f"""

**How it works:**
If a user sends more than {settings['limit']} messages in {settings['time_window']} seconds, they will be {settings['action']}d automatically.

**Commands:**
• `/setflood <number>` - Set message limit
• `/setfloodmode <action>` - Set action (mute/kick/ban)
• `/flood` - Show current settings"""

    await update.message.reply_text(flood_info, parse_mode='Markdown')


async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is flooding and take action"""
    if not update.message or not update.effective_user:
        return False

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user

    # Skip admins, whitelisted and approved users
    if (db.is_admin(user_id, chat_id) or db.is_whitelisted(user_id, chat_id)
            or db.is_approved(user_id, chat_id)):
        return False

    # Check for flood
    if flood_control.add_message(chat_id, user_id):
        settings = get_flood_settings(chat_id)

        try:
            if settings['action'] == 'mute':
                until_date = datetime.now() + timedelta(seconds=settings['duration'])
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                db.add_mute(user_id, chat_id, context.bot.id, settings['duration'], "Flood protection")

                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been muted for {format_time_duration(settings['duration'])} due to flooding!"
                )

            elif settings['action'] == 'kick':
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)

                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been kicked due to flooding!"
                )

            elif settings['action'] == 'ban':
                await context.bot.ban_chat_member(chat_id, user_id)
                db.add_ban(user_id, chat_id, context.bot.id, "Flood protection")

                action_msg = await context.bot.send_message(
                    chat_id,
                    f"🌊 {user.first_name} has been banned due to flooding!"
                )

            # Delete the action message after 5 seconds
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat_id, action_msg.message_id),
                5
            )

            logger.info(f"Flood protection: {settings['action']}ed user {user_id} in chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Error applying flood protection: {e}")

    return False


@is_admin_command
@is_group_command
async def antiraid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Configure anti-raid protection.

    /antiraid on|off
    /antiraid set <threshold> <window_seconds>
    /antiraid status
    """
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "🛡️ **Anti-Raid**\n\n"
            "Auto-enables under-attack mode when many users join quickly.\n\n"
            "**Commands:**\n"
            "• `/antiraid on` — enable\n"
            "• `/antiraid off` — disable\n"
            "• `/antiraid set <threshold> <window>` — e.g. `/antiraid set 10 60`\n"
            "• `/antiraid status` — show current settings",
            parse_mode='Markdown',
        )
        return

    sub = context.args[0].lower()
    if sub in ('on', 'off', 'enable', 'disable'):
        val = sub in ('on', 'enable')
        set_raid_settings(chat_id, enabled=val)
        await update.message.reply_text(f"🛡️ Anti-raid {'enabled' if val else 'disabled'}.")
    elif sub == 'status':
        s = get_raid_settings(chat_id)
        await update.message.reply_text(
            f"🛡️ **Anti-Raid Settings**\n\n"
            f"**Status:** {'✅ Enabled' if s['enabled'] else '❌ Disabled'}\n"
            f"**Threshold:** {s['threshold']} joins\n"
            f"**Window:** {s['window']}s\n"
            f"**Under-attack duration:** {format_time_duration(s['duration'])}",
            parse_mode='Markdown',
        )
    elif sub == 'set':
        if len(context.args) < 3 or not context.args[1].isdigit() or not context.args[2].isdigit():
            await update.message.reply_text("❌ Usage: `/antiraid set <threshold> <window_seconds>`", parse_mode='Markdown')
            return
        threshold = int(context.args[1])
        window = int(context.args[2])
        set_raid_settings(chat_id, threshold=threshold, window=window, enabled=True)
        await update.message.reply_text(
            f"✅ Anti-raid set to trigger under-attack mode after {threshold} joins within {window}s."
        )
    else:
        await update.message.reply_text("❌ Unknown option. Use: on, off, set, status")


async def check_raid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Track joins. If anti-raid triggers, enable under-attack mode for the chat.
    Returns True if a raid was detected (and the join messages should be removed).
    """
    if not update.message or not update.message.new_chat_members:
        return False

    chat_id = update.effective_chat.id
    settings = get_raid_settings(chat_id)
    if not settings['enabled']:
        return False

    now = datetime.now()
    joins = _raid_tracker[chat_id]
    joins.append(now)
    cutoff = now - timedelta(seconds=settings['window'])
    _raid_tracker[chat_id] = [t for t in joins if t >= cutoff]

    if len(_raid_tracker[chat_id]) >= settings['threshold']:
        # Enable under-attack mode
        session = db.get_session()
        try:
            chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
            if chat:
                chat.under_attack = True
                chat.is_silenced = True
                session.commit()
        finally:
            session.close()

        try:
            await context.bot.send_message(
                chat_id,
                "🚨 **RAID DETECTED!**\n"
                "Under-attack mode has been enabled (auto-disables after a while).\n"
                "New members will be kicked until the chat is safe."
            )
        except Exception:
            pass

        def _disable(context, cid=chat_id):
            s = db.get_session()
            try:
                chat = s.query(db.Chat).filter(db.Chat.id == cid).first()
                if chat:
                    chat.under_attack = False
                    chat.is_silenced = False
                    s.commit()
            finally:
                s.close()

        context.job_queue.run_once(_disable, settings['duration'])

        # Clear the tracker for this burst
        _raid_tracker[chat_id] = []
        return True

    return False


# Initialize table
update_antiflood_database()
