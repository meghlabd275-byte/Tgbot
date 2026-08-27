"""
Connections module — mirrors Rose's /connect system.

Lets an admin manage a group's settings from a private chat with the bot.
An admin can connect their private chat to any group the bot is in (and in
which they are an admin), then use the bot's admin/settings commands there
without having to be inside the group.

Usage:
  /connect <group id or @username>   (in private)  -> connect to a group
  /connect                            (in group)    -> get a connect button
  /disconnect                                          -> clear connection
  /connection                                          -> show current connection
  /reconnect                                           -> reconnect to last group
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import db
from utils import is_telegram_admin

logger = logging.getLogger(__name__)

# In-memory connection map: user_id -> chat_id
_active_connections = {}
_recent_connections = {}  # user_id -> list of chat_ids (most recent first)


def get_connection(user_id: int):
    return _active_connections.get(user_id)


def set_connection(user_id: int, chat_id: int):
    _active_connections[user_id] = chat_id
    recent = _recent_connections.setdefault(user_id, [])
    if chat_id in recent:
        recent.remove(chat_id)
    recent.insert(0, chat_id)
    recent[:] = recent[:5]


def clear_connection(user_id: int):
    return _active_connections.pop(user_id, None)


async def resolve_chat(context: ContextTypes.DEFAULT_TYPE, arg: str):
    """Resolve a group from an id or @username string. Returns chat or None."""
    if not arg:
        return None
    arg = arg.strip()
    if arg.startswith('@'):
        try:
            return await context.bot.get_chat(arg)
        except Exception:
            return None
    if arg.lstrip('-').isdigit():
        try:
            return await context.bot.get_chat(int(arg))
        except Exception:
            return None
    return None


async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Connect private chat to a group, or emit a button when used in a group."""
    user_id = update.effective_user.id
    chat = update.effective_chat

    if chat.type == 'private':
        if not context.args:
            # Show current connection and recent groups
            current = get_connection(user_id)
            msg = "🔗 **Connections**\n\n"
            if current:
                title = None
                try:
                    g = await context.bot.get_chat(current)
                    title = g.title
                except Exception:
                    pass
                msg += f"**Currently connected to:** `{current}` ({title or 'unknown'})\n\n"
            else:
                msg += "You are not connected to any group.\n\n"

            recent = _recent_connections.get(user_id, [])
            if recent:
                msg += "**Recent groups:**\n"
                for cid in recent[:5]:
                    title = None
                    try:
                        g = await context.bot.get_chat(cid)
                        title = g.title
                    except Exception:
                        pass
                    msg += f"• `{cid}` ({title or 'unknown'})\n"
                msg += "\n"
            msg += ("Usage:\n"
                    "• `/connect <group id or @username>` — connect to a group\n"
                    "• `/connect` (in the group) — get a connect button\n"
                    "• `/disconnect` — clear connection\n"
                    "• `/connection` — show current connection\n"
                    "• `/reconnect` — reconnect to your last group")
            await update.message.reply_text(msg, parse_mode='Markdown')
            return

        target = await resolve_chat(context, context.args[0])
        if not target:
            await update.message.reply_text("❌ Could not find that chat. Make sure I'm a member and the ID/username is correct.")
            return

        # Verify the user is an admin in that target group
        if not await is_telegram_admin(context, target.id, user_id):
            await update.message.reply_text("❌ You must be an admin of that group to connect to it.")
            return

        set_connection(user_id, target.id)
        await update.message.reply_text(
            f"✅ Connected to **{target.title}** (`{target.id}`).\n"
            f"You can now use my admin/settings commands here in private.",
            parse_mode='Markdown',
        )
        return

    # Group context: give an inline button to connect
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Connect to this group", callback_data=f"connect_{chat.id}")
    ]])
    await update.message.reply_text(
        "Press the button below to connect your private chat to this group, "
        "then manage its settings from private.",
        reply_markup=keyboard,
    )


async def handle_connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith('connect_'):
        return
    chat_id = int(data.split('_', 1)[1])
    user_id = query.from_user.id

    if not await is_telegram_admin(context, chat_id, user_id):
        await query.answer("❌ You must be an admin of this group to connect.", show_alert=True)
        return

    set_connection(user_id, chat_id)
    await query.answer("✅ Connected! Now use admin commands in private chat.", show_alert=True)


async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    removed = clear_connection(user_id)
    if removed:
        await update.message.reply_text("✅ Disconnected from the group.")
    else:
        await update.message.reply_text("ℹ️ You weren't connected to any group.")


async def connection_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_connection(user_id)
    if not current:
        await update.message.reply_text("ℹ️ You are not connected to any group.")
        return
    title = None
    try:
        g = await context.bot.get_chat(current)
        title = g.title
    except Exception:
        pass
    await update.message.reply_text(
        f"🔗 **Current connection**\n\n"
        f"• Group: {title or 'unknown'}\n"
        f"• ID: `{current}`",
        parse_mode='Markdown',
    )


async def reconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    recent = _recent_connections.get(user_id, [])
    # Find the first recent group the user is still an admin of
    for cid in recent:
        if await is_telegram_admin(context, cid, user_id):
            set_connection(user_id, cid)
            title = None
            try:
                g = await context.bot.get_chat(cid)
                title = g.title
            except Exception:
                pass
            await update.message.reply_text(
                f"✅ Reconnected to {title or 'group' } (`{cid}`).",
                parse_mode='Markdown',
            )
            return
    await update.message.reply_text("❌ No previous group found where you are still an admin.")


def get_effective_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Resolve the chat a command should act on.

    In a private chat, if the user is connected to a group, route admin/settings
    commands to that connected group. Otherwise use the effective chat.
    """
    chat = update.effective_chat
    if chat.type == 'private':
        connected = get_connection(update.effective_user.id)
        if connected:
            return connected
    return chat.id
