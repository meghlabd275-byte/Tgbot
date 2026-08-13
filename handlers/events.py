from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from database import db
import logging

logger = logging.getLogger(__name__)

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the chat"""
    chat_id = update.effective_chat.id
    
    # Check if chat is under attack
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat and chat.under_attack:
            # Kick all new members when under attack
            for member in update.message.new_chat_members:
                try:
                    await context.bot.ban_chat_member(chat_id, member.id)
                    await context.bot.unban_chat_member(chat_id, member.id)
                    logger.info(f"Kicked new member {member.id} due to under attack mode in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to kick new member {member.id}: {e}")
            
            # Delete the join message
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
            return
        
        # Check for global bans
        for member in update.message.new_chat_members:
            if db.is_banned(member.id):
                try:
                    await context.bot.ban_chat_member(chat_id, member.id)
                    logger.info(f"Banned new member {member.id} due to global ban in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to ban globally banned member {member.id}: {e}")
            else:
                # Register new user
                db.get_or_create_user(member.id, member.username, member.first_name, member.last_name)
    
    finally:
        session.close()

async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle members leaving the chat"""
    # Update user last active time
    left_member = update.message.left_chat_member
    if left_member:
        db.get_or_create_user(left_member.id, left_member.username, left_member.first_name, left_member.last_name)

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
    
    # Handle admin promotions/demotions
    if old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED] and \
       new_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        # User was promoted to admin
        logger.info(f"User {user_id} was promoted to admin in chat {chat_id}")
        
    elif old_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and \
         new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        # User was demoted from admin
        logger.info(f"User {user_id} was demoted from admin in chat {chat_id}")
        # Remove from bot admin list
        db.remove_admin(user_id, chat_id)
    
    # Handle bans
    elif new_status in [ChatMemberStatus.BANNED, ChatMemberStatus.KICKED]:
        logger.info(f"User {user_id} was banned/kicked from chat {chat_id}")
    
    # Handle unbans
    elif old_status in [ChatMemberStatus.BANNED, ChatMemberStatus.KICKED] and \
         new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        logger.info(f"User {user_id} was unbanned in chat {chat_id}")

async def handle_bot_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when the bot is added to a new chat"""
    chat = update.effective_chat
    
    # Register the chat
    db.get_or_create_chat(chat.id, chat.title)
    
    # Send welcome message
    welcome_msg = (
        f"👋 **Hello! I'm your new admin assistant bot.**\n\n"
        f"🔧 **To get started:**\n"
        f"1. Make me an admin with necessary permissions\n"
        f"2. Use `/activate` to register this chat\n"
        f"3. Use `/help` to see all available commands\n\n"
        f"🛡️ **I can help you with:**\n"
        f"• User management (ban, kick, mute, warn)\n"
        f"• Chat moderation (silence, purge, pin)\n"
        f"• Admin verification and security\n"
        f"• Whitelist and reputation systems\n\n"
        f"📚 Use `/help` for a complete command list!"
    )
    
    try:
        await context.bot.send_message(chat.id, welcome_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to send welcome message to chat {chat.id}: {e}")

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