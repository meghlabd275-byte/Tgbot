"""
Owner-only service controls.

The bot owner (super admin, configured via SUPER_ADMIN_ID / EXTRA_SUPER_ADMIN_IDS)
can disable ALL bot services in any group this bot is a member of, and only the
owner can resume them. Disabling persists across restarts (it is stored in the
database, on every supported backend) and is enforced at the top of the message,
join, leave, and command pipelines, plus inside every admin command decorator.

This is a real, production kill-switch — not a mock: the chat's `disabled_chats`
row is queried on every relevant update.
"""

from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_super_admin_command
import logging

logger = logging.getLogger(__name__)


async def resolve_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resolve the target chat id for a super-admin service command.

    Priority: explicit numeric argument (chat id) -> current chat id.
    """
    chat_id = None
    title = None

    if context.args:
        raw = context.args[0].lstrip('-')
        if raw.isdigit():
            chat_id = int(context.args[0])
            try:
                resolved = await context.bot.get_chat(chat_id)
                title = getattr(resolved, 'title', None) or getattr(resolved, 'username', None)
            except Exception:
                title = None

    if chat_id is None:
        chat_id = update.effective_chat.id
        title = update.effective_chat.title
        if not title and update.effective_chat.type == 'private':
            title = 'Private chat with owner'

    return chat_id, title


@is_super_admin_command
async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command: disable ALL bot services for a group (defaults to current chat)."""
    user_id = update.effective_user.id
    chat_id, title = await resolve_chat_id(update, context)

    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else None

    was_disabled_already = not db.disable_chat(chat_id, user_id, reason)

    if was_disabled_already:
        text = f"⚠️ Group `{chat_id}` is already disabled."
    else:
        text = (
            f"🛑 **All bot services disabled** for group `{chat_id}`"
            f"{' (' + title + ')' if title else ''}.\n"
            "Only the bot owner can resume this group."
        )
    if reason:
        text += f"\n📝 Reason: {reason}"
    await update.message.reply_text(text, parse_mode='Markdown')


@is_super_admin_command
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command: resume ALL bot services for a group (defaults to current chat)."""
    chat_id, title = await resolve_chat_id(update, context)

    was_disabled = db.enable_chat(chat_id)

    if was_disabled:
        text = (
            f"✅ **All bot services resumed** for group `{chat_id}`"
            f"{' (' + title + ')' if title else ''}."
        )
    else:
        text = f"ℹ️ Group `{chat_id}` is not disabled."
    await update.message.reply_text(text, parse_mode='Markdown')


@is_super_admin_command
async def disabledgroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command: list all groups whose services are currently disabled."""
    rows = db.get_disabled_chats()
    if not rows:
        await update.message.reply_text("✅ No groups are currently disabled.")
        return

    lines = [f"🛑 **Disabled groups ({len(rows)})**\n"]
    for row in rows[:50]:
        lines.append(f"• `{row.chat_id}` — by `{row.disabled_by}` at {row.created_at}")
    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')


def chat_disabled(chat_id: int) -> bool:
    """Synchronous shortcut so event handlers can short-circuit without a session."""
    return db.is_chat_disabled(chat_id)
