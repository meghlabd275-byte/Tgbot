"""
Shared moderation helpers used by warning_system, filters, reports, etc.

Centralizes the warning-limit consequence logic so warn_mode (kick/ban/mute/
tban) is honored anywhere warnings are handed out.
"""
import logging
from datetime import datetime, timedelta

from telegram import ChatPermissions
from telegram.ext import ContextTypes

from database import db
from utils import format_time_duration

logger = logging.getLogger(__name__)


async def apply_warn_consequence(chat_id: int, user_id: int, actor_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Apply the configured warn_mode to a user that has reached the warning
    limit. Returns a human-readable description of the action taken (or '').
    """
    settings = db.get_warn_settings(chat_id)
    mode = settings.get('mode', 'ban')

    try:
        if mode == 'kick':
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            return "kicked"
        elif mode == 'mute':
            until_date = datetime.now() + timedelta(hours=1)
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            db.add_mute(user_id, chat_id, actor_id, 3600, "Warning limit reached")
            return "muted for 1 hour"
        elif mode == 'tban':
            until_date = datetime.now() + timedelta(days=1)
            await context.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
            db.add_ban(user_id, chat_id, actor_id, "Warning limit reached (temp ban)")
            return "temporarily banned for 1 day"
        else:  # 'ban' default
            await context.bot.ban_chat_member(chat_id, user_id)
            db.add_ban(user_id, chat_id, actor_id, "Warning limit reached")
            return "banned"
    except Exception as e:
        logger.error(f"apply_warn_consequence failed for user {user_id} in {chat_id} ({mode}): {e}")
        return ""


def set_warn_mode_command_response(chat_id: int, mode: str):
    """Persist warn_mode and return a friendly confirmation message."""
    db.set_warn_mode(chat_id, mode)
    labels = {
        'kick': 'kick at warning limit',
        'mute': 'mute for 1 hour at warning limit',
        'tban': 'temporarily ban for 1 day at warning limit',
        'ban': 'ban at warning limit',
    }
    return f"✅ Warn mode set: **{labels.get(mode, mode)}**"


VALID_WARN_MODES = ('kick', 'ban', 'mute', 'tban')
