"""
User Commands system (mirrors Rose's custom-command feature, with admin control).

Group admins decide what commands regular members can run:

* ``/usercmd add|new <name> <response...>`` — create a member-usable command
* ``/usercmd del|remove <name>``                 — delete a member command
* ``/usercmd list``                              — shows usage AND the handler as entered
* ``/usercmd on|start|enable <name>``            — activate a member command
* ``/usercmd off|stop|disable <name>``           — deactivate a member command
* ``/usercmd setup <name> <response...>``        — update the response of an existing command

Members invoke one simply by typing ``!name`` (or the configured symbol) in the
group. Only the commands the admins have enabled are answered.
"""
import logging

from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Text
from sqlalchemy.sql import func

from telegram import Update
from telegram.ext import ContextTypes

from database import Base, db
from utils import is_admin_command, is_group_command

logger = logging.getLogger(__name__)


class UserCommand(Base):
    __tablename__ = 'user_commands'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    name = Column(String(64))
    response = Column(Text)
    trigger = Column(String(16), default='!')   # prefix that activates the command
    enabled = Column(Boolean, default=True)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def update_user_commands_database():
    Base.metadata.create_all(bind=db.engine)


def _clean_name(raw: str) -> str:
    raw = (raw or '').strip().lstrip('!')
    return raw.lower()


def _split_trigger_args(args) -> tuple:
    """Allow ``/usercmd add !name ...`` — if the first arg ends with '+', it's
    the trigger; otherwise return default trigger and args untouched."""
    if not args:
        return '!', []
    return '!', list(args)


async def _resolve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = list(context.args or [])

    if not args:
        await update.message.reply_text(
            "❌ Usage:\n"
            "`/usercmd add <name> <response>`\n"
            "`/usercmd del <name>`\n"
            "`/usercmd on|off <name>`\n"
            "`/usercmd setup <name> <response>`\n"
            "`/usercmd list`",
            parse_mode='Markdown',
        )
        return chat_id, None, None

    op = args[0].lower()
    if op in ('list', 'l'):
        return chat_id, 'list', None

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage:\n"
            f"`/usercmd {op} <name> [response]`",
            parse_mode='Markdown',
        )
        return chat_id, None, None

    name = _clean_name(args[1])
    if not name:
        await update.message.reply_text("❌ Please provide a command name.")
        return chat_id, None, None

    return chat_id, op, name


@is_admin_command
@is_group_command
async def usercmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin control panel for member-usable custom commands."""
    chat_id, op, name = await _resolve_command(update, context)
    if op is None:
        return

    session = db.get_session()
    try:
        # -------- list --------
        if op == 'list':
            rows = session.query(UserCommand).filter(UserCommand.chat_id == chat_id).order_by(UserCommand.name).all()
            if not rows:
                await update.message.reply_text("📋 No user commands configured yet.\nUse `/usercmd add <name> <response>` to create one.")
                return
            lines = ["📋 **User Commands (member-usable):**", ""]
            for r in rows:
                status = "🟢" if r.enabled else "🔴"
                lines.append(f"{status} {r.trigger}{r.name} — `{r.response[:80]}{'…' if len(r.response) > 80 else ''}`")
            lines.append("")
            lines.append("**Usage:** just type `!commandname` in the group.")
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
            return

        trigger, _rest = _split_trigger_args(context.args)

        # -------- add / new --------
        if op in ('add', 'new'):
            response = ' '.join(context.args[2:]).strip()
            if not response:
                await update.message.reply_text(
                    "❌ Please provide a response.\n"
                    f"Usage: `/usercmd add {name} <response>`",
                    parse_mode='Markdown',
                )
                return
            existing = session.query(UserCommand).filter(
                UserCommand.chat_id == chat_id,
                UserCommand.name == name,
            ).first()
            if existing:
                await update.message.reply_text(
                    f"❌ Command `{trigger}{name}` already exists. Use `/usercmd setup {name} <response>` to change it."
                )
                return
            session.add(UserCommand(
                chat_id=chat_id,
                name=name,
                response=response,
                trigger=trigger,
                enabled=True,
                created_by=update.effective_user.id,
            ))
            session.commit()
            await update.message.reply_text(
                f"✅ User command `{trigger}{name}` created.\nMembers can use it by typing `{trigger}{name}` in the group."
            )

        # -------- del / remove --------
        elif op in ('del', 'remove'):
            row = session.query(UserCommand).filter(
                UserCommand.chat_id == chat_id,
                UserCommand.name == name,
            ).first()
            if not row:
                await update.message.reply_text(f"❌ Command `{name}` does not exist.")
                return
            session.delete(row)
            session.commit()
            await update.message.reply_text(f"✅ User command `{trigger}{name}` deleted.")

        # -------- on / start / enable --------
        elif op in ('on', 'start', 'enable'):
            row = session.query(UserCommand).filter(
                UserCommand.chat_id == chat_id,
                UserCommand.name == name,
            ).first()
            if not row:
                await update.message.reply_text(
                    f"❌ Command `{trigger}{name}` does not exist. Create it first with `/usercmd add {name} <response>`."
                )
                return
            row.enabled = True
            session.commit()
            await update.message.reply_text(f"🟢 User command `{trigger}{name}` enabled.")

        # -------- off / stop / disable --------
        elif op in ('off', 'stop', 'disable'):
            row = session.query(UserCommand).filter(
                UserCommand.chat_id == chat_id,
                UserCommand.name == name,
            ).first()
            if not row:
                await update.message.reply_text(f"❌ Command `{name}` does not exist.")
                return
            row.enabled = False
            session.commit()
            await update.message.reply_text(f"🔴 User command `{trigger}{name}` disabled.")

        # -------- setup --------
        elif op in ('setup', 'set'):
            response = ' '.join(context.args[2:]).strip()
            row = session.query(UserCommand).filter(
                UserCommand.chat_id == chat_id,
                UserCommand.name == name,
            ).first()
            if not row:
                await update.message.reply_text(
                    f"❌ Command `{name}` does not exist. Create it with `/usercmd add {name} <response>`."
                )
                return
            if not response:
                await update.message.reply_text(
                    f"❌ Please provide a new response.\nUsage: `/usercmd setup {name} <response>`"
                )
                return
            row.response = response
            session.commit()
            await update.message.reply_text(f"✅ Response for `{trigger}{name}` updated.")

        else:
            await update.message.reply_text(
                "❌ Unknown operation. Use: `add`, `del`, `list`, `on`, `off`, or `setup`."
            )

    finally:
        session.close()


async def handle_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Respond to ``!name`` invocations in groups. Returns True if handled."""
    text = (update.message.text or '') if update.message else ''
    if not text.startswith('!'):
        return False

    stripped = text[1:].strip()
    if not stripped:
        return False

    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        row = session.query(UserCommand).filter(
            UserCommand.chat_id == chat_id,
            UserCommand.name == stripped.lower(),
            UserCommand.enabled == True,
        ).first()
        if not row:
            return False
        await update.message.reply_text(row.response, parse_mode='Markdown')
        return True
    finally:
        session.close()


update_user_commands_database()
