from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from database import db
from utils import sync_telegram_admins
import logging

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages for various checks"""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    # Update user info and last active
    db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)

    # Skip processing for private chats
    if chat.type == 'private':
        return

    # Track message activity for /stats and /top leaderboards (only for
    # registered chats and only non-command text messages).
    if message.text and not message.text.startswith('/'):
        try:
            from handlers.stats import increment_message_count
            increment_message_count(chat.id, user.id)
        except Exception as e:
            logger.error(f"Failed to increment message count: {e}")

    # Check if chat is registered
    session = db.get_session()
    try:
        chat_obj = session.query(db.Chat).filter(db.Chat.id == chat.id).first()
        if not chat_obj:
            return  # Chat not registered

        # Check if user is muted
        if db.is_muted(user.id, chat.id):
            try:
                await context.bot.delete_message(chat.id, message.message_id)
                logger.info(f"Deleted message from muted user {user.id} in chat {chat.id}")
            except Exception as e:
                logger.error(f"Failed to delete message from muted user: {e}")
            return

        # Check if chat is silenced and user is not admin
        if chat_obj.is_silenced and not db.is_admin(user.id, chat.id):
            try:
                await context.bot.delete_message(chat.id, message.message_id)
                logger.info(f"Deleted message from non-admin {user.id} in silenced chat {chat.id}")
            except Exception as e:
                logger.error(f"Failed to delete message in silenced chat: {e}")
            return

        # Check for spam/flood (basic implementation)
        # This could be expanded with more sophisticated anti-spam measures

    finally:
        session.close()

async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chat member status updates (promotions, demotions, etc.)"""
    if not update.chat_member:
        return

    chat_id = update.effective_chat.id
    user_id = update.chat_member.new_chat_member.user.id
    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status

    # Attribute joins made via an invite link so /link_stat can report totals.
    if (old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED) and
            new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED)):
        invite_link = getattr(update.chat_member, 'invite_link', None)
        invite_name = getattr(invite_link, 'name', None)
        if invite_name:
            try:
                from handlers.invite_links import record_join_from_chat_member
                record_join_from_chat_member(chat_id, user_id, invite_name)
                logger.info(f"Attributed join of {user_id} to invite link '{invite_name}'")
            except Exception as e:
                logger.error(f"Failed to attribute invite-link join: {e}")

    # Handle admin promotions/demotions
    if old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED] and \
       new_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        # User was promoted to admin
        logger.info(f"User {user_id} was promoted to admin in chat {chat_id}")
        user = update.chat_member.new_chat_member.user
        db.get_or_create_chat(chat_id)
        db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
        db.add_admin(user.id, chat_id)
    elif old_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
         new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        # User was demoted from admin
        logger.info(f"User {user_id} was demoted from admin in chat {chat_id}")
        # Remove from bot admin list
        db.remove_admin(user_id, chat_id)

    # Handle bans/kicks (Telegram reports both as ChatMemberStatus.BANNED == 'kicked')
    elif new_status == ChatMemberStatus.BANNED:
        logger.info(f"User {user_id} was banned/kicked from chat {chat_id}")

    # Handle unbans
    elif old_status == ChatMemberStatus.BANNED and \
         new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED):
        logger.info(f"User {user_id} was unbanned in chat {chat_id}")

async def handle_bot_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the bot being added to (or removed from) a chat."""
    chat = update.effective_chat
    new_member = update.my_chat_member.new_chat_member if update.my_chat_member else None

    # Ignore the "removed from chat" / "kicked/banned" cases.
    if new_member and new_member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        logger.info(f"Bot removed from chat {chat.id} ({chat.title})")
        return

    # Register the chat and sync its admins so the admin who added the bot can
    # configure this group immediately. (The actual "I'm your new assistant bot"
    # announcement is sent by handle_new_member_welcome, which owns the bot-added
    # path via the NEW_CHAT_MEMBERS service message. We do NOT announce here,
    # otherwise the bot would greet the group redundantly — and again on every
    # MY_CHAT_MEMBER change, e.g. when it is promoted to admin.)
    db.get_or_create_chat(chat.id, chat.title)
    await sync_telegram_admins(context, chat.id)
    logger.info(f"Bot added to chat {chat.id} ({chat.title}); chat registered and admins synced")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")

    # Try to send error message to user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )
        except:
            pass