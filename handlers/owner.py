"""
Super-admin (owner) fleet commands.

Everything here is strictly owner-only. Group admins cannot use any of it.

Commands provided:

    /groups                  — list every Telegram group any fleet bot is in,
                               with the number of days each group has been
                               using the bot.
    /clone                   — interactive flow to register a live clone bot
                               from just a bot token + bot username.
    /clone_bots              — list all registered clone bots with live status.
    /bot start|stop|pause|resume|enable|disable|status <id|@username>
                             — manage a single clone from Telegram.
    /botdel <id|@username>   — permanently remove a clone from the registry.
    /commands                — full command documentation (enhanced version).

The super-admin identity comes from ``Config.super_admin_ids()`` (set via
SUPER_ADMIN_ID / EXTRA_SUPER_ADMIN_IDS in the environment). Because clone bots
share the same process, the same owner id list applies fleet-wide.
"""
import logging
import re
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import ContextTypes, ConversationHandler

from config import Config
from database import db
from utils import is_super_admin_command

logger = logging.getLogger(__name__)

# Conversation states for /clone
AWAIT_TOKEN, AWAIT_USERNAME = range(2)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_owner(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in Config.super_admin_ids()


def is_owner_chat(update: Update) -> bool:
    return is_owner(update) and update.effective_chat.type == 'private'


def parse_bot_token(token: str) -> bool:
    """Very basic shape check: '<digits>:<anything>'."""
    token = (token or '').strip()
    if not token:
        return False
    match = re.match(r'^(\d+):[A-Za-z0-9_\-]+$', token)
    return bool(match)


def normalize_username(username: str) -> str:
    """Normalize a Telegram username (strip quotes, optional '@' / t.me/ link).

    Only the FINAL '@' prefix and a literal 't.me/' prefix are removed so the
    username itself is never mangled (e.g. '@MysBot' stays 'mysbot').
    """
    username = (username or '').strip().lower()
    if username.startswith('t.me/'):
        username = username[len('t.me/'):]
    # Strip a single leading '@' (in case multiple were pasted).
    while username.startswith('@'):
        username = username[1:]
    return username


def _days_between(start, now=None) -> int:
    if not start:
        return 0
    try:
        now = now or datetime.now()
        if now.tzinfo is None and start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        delta = now - start
        return max(int(delta.total_seconds() // 86400), 0)
    except Exception:
        return 0


def _format_member_count(count: int) -> str:
    return f"{count}" if count < 1000 else f"{count // 1000}.{count % 1000 // 100}k"


def _status_emoji(status: str) -> str:
    return {
        'active': '🟢',
        'paused': '🟡',
        'disabled': '🔴',
    }.get(status or 'disabled', '⚪')


async def _resolve_bot_me(token: str):
    """Resolve the bot identity (id + username) from a token using the API.

    Returns (bot_id, username) or (None, None) on failure.
    """
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        return me.id, me.username
    except Exception as e:
        logger.info("Token validation failed: %s", e)
        return None, None


def _format_clone_row(row, runtime_status: str = None) -> str:
    status = row.status or 'disabled'
    if runtime_status:
        status = runtime_status
    name = row.display_name or row.username
    return (
        f"{_status_emoji(status)} `{row.id}` · @{row.username} · {status}"
    )


# ---------------------------------------------------------------------------
# /clone — interactive registration flow (owner, private chat)
# ---------------------------------------------------------------------------


async def clone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner_chat(update):
        await update.message.reply_text(
            f"❌ This command is reserved for the bot owner. Your id:"
            f" `{update.effective_user.id}`"
        )
        return ConversationHandler.END

    if context.args and parse_bot_token(context.args[0]):
        # Token passed as an argument (e.g. /clone 123:abc).
        context.user_data['clone_token'] = context.args[0].strip()
        await update.message.reply_text(
            "🤖 **Clone a new bot — Step 2/2**\n\n"
            "Now send the **bot username** (e.g. `MyGroupHelperBot`, with or "
            "without @).\n\n"
            "Send `/cancel` to abort."
        )
        return AWAIT_USERNAME

    await update.message.reply_text(
        "🤖 **Clone a new bot — Step 1/2**\n\n"
        "Send me the **Telegram bot token** you got from @BotFather.\n\n"
        "Format: `123456789:AAH...`\n\n"
        "Send `/cancel` to abort."
    )
    return AWAIT_TOKEN


async def _clone_await_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == '/cancel':
        await update.message.reply_text("⏹ Clone cancelled.")
        return ConversationHandler.END
    if not parse_bot_token(text):
        await update.message.reply_text(
            "❌ That doesn't look like a bot token. Format: `123456789:AAH...`\n"
            "Try again, or send `/cancel` to abort."
        )
        return AWAIT_TOKEN
    context.user_data['clone_token'] = text
    await update.message.reply_text(
        "🤖 **Step 2/2** — now send the **bot username** (e.g. `MyGroupHelperBot`)."
    )
    return AWAIT_USERNAME


async def _clone_await_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == '/cancel':
        await update.message.reply_text("⏹ Clone cancelled.")
        return ConversationHandler.END

    username = normalize_username(text)
    if not username or not re.match(r'^[A-Za-z0-9_]{3,32}$', username):
        await update.message.reply_text(
            "❌ Invalid username. Bot usernames are 3–32 characters, letters, "
            "digits and underscores. Try again or send `/cancel`."
        )
        return AWAIT_USERNAME

    token = context.user_data.get('clone_token')
    if not token:
        await update.message.reply_text("❌ Session expired. Run `/clone` again.")
        return ConversationHandler.END

    # Verify the token really belongs to this username using the Bot API.
    await update.message.reply_text("⏳ Validating token with Telegram ...")
    bot_id, real_username = await _resolve_bot_me(token)

    if bot_id is None:
        await update.message.reply_text(
            "❌ **Invalid token.** Telegram rejected it. Double-check the token "
            "from @BotFather and run `/clone` again."
        )
        return ConversationHandler.END

    if username and real_username and real_username.lower() != username:
        await update.message.reply_text(
            f"❌ The token belongs to **@{real_username}**, not `{username}`. "
            "Please enter the correct username for that token."
        )
        return AWAIT_USERNAME

    # Check it isn't the main bot itself.
    if token == Config.BOT_TOKEN:
        await update.message.reply_text(
            "❌ That's the **main bot's token**. You cannot clone the main bot "
            "into itself."
        )
        return ConversationHandler.END

    row, created = db.register_bot_instance(
        token=token,
        username=real_username or username,
        bot_id=bot_id,
        display_name=None,
        created_by=update.effective_user.id,
        status='active',
    )

    if not created:
        await update.message.reply_text(
            f"ℹ️ {real_username or username} is already registered "
            f"(id `{row.id}`, status: {row.status})."
        )
    else:
        await update.message.reply_text(
            f"✅ **Live clone registered!**\n\n"
            f"• ID: `{row.id}`\n"
            f"• Username: @{real_username or username}\n"
            f"• Status: active (starting…)\n\n"
            f"Now bringing it online …"
        )

    # Bring the clone online immediately (live clone — no redeployment).
    from handlers.clonebot import is_clone_running, start_clone
    if is_clone_running(row.id):
        await update.message.reply_text(
            f"ℹ️ @{real_username or username} is already running live."
        )
    else:
        ok = start_clone(row.id)
        if ok:
            await update.message.reply_text(
                f"🚀 @{real_username or username} is now **live** with the full "
                "feature set."
            )
        else:
            await update.message.reply_text(
                f"⚠️ Could not start @{real_username or username} right now; "
                "it will be retried automatically. Use `/bot status` later."
            )

    # Re-sync group memberships across the fleet so the new clone sees every
    # group the fleet is already in.
    for membership in db.get_groups_for_bot(0):
        db.record_fleet_membership(membership.chat_id, membership.chat_title,
                                   include_bot_id=row.bot_id)

    del context.user_data['clone_token']
    return ConversationHandler.END


async def _clone_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏹ Operation cancelled.")
    return ConversationHandler.END


def clone_conversation_handler():
    """Build the ConversationHandler wiring for /clone."""
    from telegram.ext import CommandHandler, MessageHandler, filters

    return ConversationHandler(
        entry_points=[CommandHandler('clone', clone_command)],
        states={
            AWAIT_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _clone_await_token),
            ],
            AWAIT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _clone_await_username),
            ],
        },
        fallbacks=[CommandHandler('cancel', _clone_cancel)],
        allow_reentry=True,
    )


# ---------------------------------------------------------------------------
# /groups — list groups using any fleet bot
# ---------------------------------------------------------------------------


@is_super_admin_command
async def groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: list every group using the bot, with days of use."""
    groups = db.get_fleet_groups()
    if not groups:
        await update.message.reply_text(
            "📭 No groups are using the bot yet.\n\n"
            "The bot records a group as soon as it (or any clone) is added to it."
        )
        return

    lines = [f"📊 **Fleet-wide group usage ({len(groups)} groups)**\n"]
    for i, g in enumerate(groups, 1):
        days = _days_between(g['joined_at'])
        title = g['title'] or 'Untitled group'
        lines.append(f"{i}. {title}")
        lines.append(f"   🆔 `{g['chat_id']}` · 🗓 {days}d · bots: {len(g['bot_ids'])}")
    text = "\n".join(lines)

    # Telegram caps a single message at 4096 chars; keep under 3500 to be safe.
    if len(text) > 3400:
        chunks = []
        current = ""
        for line in lines:
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) > 3400:
                chunks.append(current)
                current = line
            else:
                current = candidate
        if current:
            chunks.append(current)
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')


# ---------------------------------------------------------------------------
# /clone_bots — list all clones with live status
# ---------------------------------------------------------------------------


@is_super_admin_command
async def clone_bots_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: list all registered clone bots and their status."""
    rows = db.get_bot_instances(only_known=True)
    if not rows:
        await update.message.reply_text(
            "🤖 No clone bots registered yet.\n\n"
            "Use `/clone` to add one — you only need its bot token and username."
        )
        return

    from handlers.clonebot import is_clone_running

    lines = [f"🤖 **Registered clone bots ({len(rows)})**\n"]
    for row in rows:
        running = is_clone_running(row.id)
        if running:
            runtime = '🟢 running'
        elif row.status == 'active':
            runtime = '🟢 active (starting…)'
        elif row.status == 'paused':
            runtime = '🟡 paused'
        else:
            runtime = '🔴 disabled'
        name = row.display_name or row.username
        lines.append(f"• `{row.id}` · @{row.username} — {runtime}")
    lines.append("")
    lines.append("Manage: `/bot start|stop|pause|resume|enable|disable <id>`")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


# ---------------------------------------------------------------------------
# /bot <action> <id|@username> — manage a single clone
# ---------------------------------------------------------------------------


@is_super_admin_command
async def bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: control one clone bot.

    Usage:
        /bot start <id|@username>
        /bot stop <id|@username>
        /bot pause <id|@username>
        /bot resume <id|@username>
        /bot enable <id|@username>
        /bot disable <id|@username>
        /bot status <id|@username>
    """
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/bot <action> <id or @username>`\n\n"
            "Actions: `start`, `stop`, `pause`, `resume`, `enable`, `disable`, `status`\n\n"
            "Examples:\n"
            "• `/bot start 3`\n"
            "• `/bot disable @MyHelperBot`"
        )
        return

    action = context.args[0].lower()
    target = ' '.join(context.args[1:]) if len(context.args) > 1 else None

    if action == 'status':
        await _bot_status(update, target)
        return

    if action not in ('start', 'stop', 'pause', 'resume', 'enable', 'disable'):
        await update.message.reply_text(
            f"❌ Unknown action `{action}`.\n\n"
            "Actions: `start`, `stop`, `pause`, `resume`, `enable`, `disable`, `status`"
        )
        return

    if not target:
        await update.message.reply_text(
            f"❌ Usage: `/bot {action} <id or @username>`"
        )
        return

    instance = _resolve_instance(target)
    if instance is None:
        await update.message.reply_text(
            f"❌ No clone found for `{target}`.\nUse `/clone_bots` to list registered bots."
        )
        return

    from handlers.clonebot import set_clone_status
    ok, message = set_clone_status(instance.id, action)
    emoji = "✅" if ok else "❌"
    await update.message.reply_text(
        f"{emoji} @{instance.username} (id `{instance.id}`): {message}."
    )


def _resolve_instance(target):
    """Resolve a target string ('3' or '@username') to a BotInstance row."""
    if not target:
        return None
    target = target.strip()
    if target.isdigit():
        return db.get_bot_instance_by_id(int(target))
    username = normalize_username(target)
    for row in db.get_bot_instances(only_known=True):
        if row.username and row.username.lower() == username:
            return row
    return None


async def _bot_status(update: Update, target):
    if not target:
        # Show a compact status table instead.
        rows = db.get_bot_instances(only_known=True)
        if not rows:
            await update.message.reply_text("🤖 No clone bots registered yet.")
            return
        from handlers.clonebot import is_clone_running
        lines = ["🤖 **Clone status**\n"]
        for row in rows:
            running = is_clone_running(row.id)
            live = 'running' if running else row.status or 'disabled'
            lines.append(f"• `{row.id}` · @{row.username} — {live}")
        await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
        return

    instance = _resolve_instance(target)
    if instance is None:
        await update.message.reply_text(f"❌ No clone found for `{target}`.")
        return
    from handlers.clonebot import is_clone_running
    running = is_clone_running(instance.id)
    lines = [
        f"🤖 **@{instance.username}** (id `{instance.id}`)",
        "",
        f"• Status: `{instance.status or 'disabled'}`",
        f"• Live: {'✅ running' if running else '❌ not running this process'}",
        f"• Registered: {instance.created_at}",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


# ---------------------------------------------------------------------------
# /botdel <id|@username> — permanently delete a clone
# ---------------------------------------------------------------------------


@is_super_admin_command
async def botdel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: permanently remove a clone bot from the registry."""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/botdel <id or @username>`\n"
            "This removes the clone from the fleet registry (it will stop immediately)."
        )
        return
    target = ' '.join(context.args)
    instance = _resolve_instance(target)
    if instance is None:
        await update.message.reply_text(f"❌ No clone found for `{target}`.")
        return

    from handlers.clonebot import is_clone_running, stop_clone
    if is_clone_running(instance.id):
        stop_clone(instance.id, mark='disabled')
    db.delete_bot_instance(instance.id)
    await update.message.reply_text(
        f"🗑 @{instance.username} (id `{instance.id}`) was removed from the fleet."
    )


# ---------------------------------------------------------------------------
# /commands — full command documentation (super-admin aware)
# ---------------------------------------------------------------------------


def _super_admin_commands_doc() -> str:
    return (
        "👑 **Super Admin / Owner Commands**\n"
        "\n"
        "These commands are reserved for the bot owner (SUPER_ADMIN_ID). "
        "Group admins cannot use them. All can be used from Telegram — "
        "preferably in private chat with the bot.\n"
        "\n"
        "**Fleet monitoring**\n"
        "• `/groups` — List every Telegram group that uses this bot (or any "
        "clone), with the number of days each group has been using it.\n"
        "\n"
        "**Clone management**\n"
        "• `/clone` — Register a *live* clone bot. You only provide the bot "
        "token and bot username (from @BotFather). No deployment is needed; "
        "the clone instantly runs the full feature set of the main bot.\n"
        "• `/clone_bots` — List all registered clone bots, their IDs and live "
        "status.\n"
        "• `/bot start <id|@username>` — Start a clone (bring it online).\n"
        "• `/bot stop <id|@username>` — Stop a clone (it stops polling).\n"
        "• `/bot pause <id|@username>` — Pause a clone (temporary stop).\n"
        "• `/bot resume <id|@username>` — Resume a paused clone.\n"
        "• `/bot enable <id|@username>` — Enable a disabled clone (starts it).\n"
        "• `/bot disable <id|@username>` — Disable a clone permanently.\n"
        "• `/bot status [id|@username]` — Show the status of a clone (or all).\n"
        "• `/botdel <id|@username>` — Permanently remove a clone from the "
        "registry.\n"
        "\n"
        "**Service controls (groups)**\n"
        "• `/disable [chat_id]` / `/disableservices` — Disable ALL bot services "
        "in a group.\n"
        "• `/resume [chat_id]` / `/resumeservices` — Resume services in a "
        "disabled group (group admins cannot).\n"
        "• `/disabledgroups` — List all groups whose services are currently "
        "disabled.\n"
        "\n"
        "**Setup tips**\n"
        "1. Send `/clone`, then paste the bot token, then the username.\n"
        "2. The clone starts instantly; add it to a group and grant it admin "
        "permissions.\n"
        "3. Use `/clone_bots` to see it live, and `/bot ...` to control it.\n"
        "4. Use `/groups` to monitor group usage across the whole fleet.\n"
    )


# ---------------------------------------------------------------------------
# Export a plain registry of owner commands for documentation/tests.
# ---------------------------------------------------------------------------

OWNER_COMMANDS = [
    ('groups', 'List every group using the bot fleet, with days of usage'),
    ('clone', 'Register a live clone bot (token + username only)'),
    ('clone_bots', 'List all registered clone bots with live status'),
    ('bot', 'Control one clone: start/stop/pause/resume/enable/disable/status'),
    ('botdel', 'Permanently delete a clone from the registry'),
    ('commands', 'Show the full super-admin command documentation'),
]