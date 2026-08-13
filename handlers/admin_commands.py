from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from database import db
from utils import is_admin_command, is_group_command, get_file_id_from_message
import logging

logger = logging.getLogger(__name__)

async def fileid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get file ID from replied message"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a media message to get its file ID.")
        return
    
    file_id = get_file_id_from_message(update.message.reply_to_message)
    if file_id:
        await update.message.reply_text(f"📎 **File ID:**\n`{file_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ No media file found in the replied message.")

@is_group_command
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register the current chat"""
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin in the chat
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await update.message.reply_text("❌ You need to be an admin to activate this chat.")
            return
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        await update.message.reply_text("❌ Error checking admin permissions.")
        return
    
    # Register chat and user
    db.get_or_create_chat(chat.id, chat.title)
    db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Add user as admin
    db.add_admin(user.id, chat.id)
    
    await update.message.reply_text(
        f"✅ Chat **{chat.title}** has been activated!\n"
        f"👤 {user.first_name} has been registered as an admin.",
        parse_mode='Markdown'
    )

@is_admin_command
@is_group_command
async def silence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silence the chat - only admins can speak"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat:
            chat.is_silenced = True
            session.commit()
            await update.message.reply_text("🔇 Chat has been silenced. Only admins can speak now.")
        else:
            await update.message.reply_text("❌ Chat not registered. Use /activate first.")
    finally:
        session.close()

@is_admin_command
@is_group_command
async def unsilence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsilence the chat - all users can speak"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat:
            chat.is_silenced = False
            session.commit()
            await update.message.reply_text("🔊 Chat has been unsilenced. All users can speak now.")
        else:
            await update.message.reply_text("❌ Chat not registered. Use /activate first.")
    finally:
        session.close()

@is_admin_command
@is_group_command
async def underattack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle under attack mode"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat:
            chat.under_attack = not chat.under_attack
            chat.is_silenced = chat.under_attack  # Auto-silence when under attack
            session.commit()
            
            if chat.under_attack:
                await update.message.reply_text(
                    "🚨 **UNDER ATTACK MODE ACTIVATED**\n"
                    "• Chat is now silenced\n"
                    "• New users will be automatically kicked\n"
                    "• Only admins can speak",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "✅ **Under attack mode deactivated**\n"
                    "• Chat restrictions lifted\n"
                    "• Normal operation resumed",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("❌ Chat not registered. Use /activate first.")
    finally:
        session.close()

# Alias for underattack
ua_command = underattack_command

@is_admin_command
async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload admin cache"""
    from utils import update_chat_admins_cache
    
    chat_id = update.effective_chat.id
    success = await update_chat_admins_cache(context, chat_id)
    
    if success:
        await update.message.reply_text("✅ Admin cache reloaded successfully.")
    else:
        await update.message.reply_text("❌ Failed to reload admin cache.")

@is_admin_command
async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Print debug information"""
    chat = update.effective_chat
    user = update.effective_user
    
    session = db.get_session()
    try:
        chat_obj = session.query(db.Chat).filter(db.Chat.id == chat.id).first()
        user_obj = session.query(db.User).filter(db.User.id == user.id).first()
        is_admin = db.is_admin(user.id, chat.id)
        
        debug_info = f"""
🔍 **Debug Information**

**Chat Info:**
• ID: `{chat.id}`
• Title: {chat.title or 'N/A'}
• Type: {chat.type}
• Registered: {'Yes' if chat_obj else 'No'}
• Silenced: {'Yes' if chat_obj and chat_obj.is_silenced else 'No'}
• Under Attack: {'Yes' if chat_obj and chat_obj.under_attack else 'No'}

**User Info:**
• ID: `{user.id}`
• Username: @{user.username or 'None'}
• Name: {user.first_name} {user.last_name or ''}
• Is Admin: {'Yes' if is_admin else 'No'}
• Registered: {'Yes' if user_obj else 'No'}

**Bot Info:**
• Username: @{context.bot.username}
• ID: `{context.bot.id}`
        """
        
        await update.message.reply_text(debug_info.strip(), parse_mode='Markdown')
    finally:
        session.close()

@is_admin_command
@is_group_command
async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pin a message"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a message to pin it.")
        return
    
    try:
        message_to_pin = update.message.reply_to_message
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=message_to_pin.message_id,
            disable_notification=False
        )
        
        # Save pinned message ID to database
        chat_id = update.effective_chat.id
        session = db.get_session()
        try:
            chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
            if chat:
                chat.pinned_message_id = message_to_pin.message_id
                session.commit()
        finally:
            session.close()
        
        await update.message.reply_text("📌 Message pinned successfully!")
        
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
        await update.message.reply_text("❌ Failed to pin message. Make sure I have admin rights.")

@is_admin_command
@is_group_command
async def unpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unpin the last pinned message"""
    try:
        chat_id = update.effective_chat.id
        
        # Get pinned message ID from database
        session = db.get_session()
        try:
            chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
            if chat and chat.pinned_message_id:
                await context.bot.unpin_chat_message(
                    chat_id=chat_id,
                    message_id=chat.pinned_message_id
                )
                chat.pinned_message_id = None
                session.commit()
                await update.message.reply_text("📌 Message unpinned successfully!")
            else:
                # Try to unpin all messages
                await context.bot.unpin_all_chat_messages(chat_id)
                await update.message.reply_text("📌 All pinned messages have been unpinned!")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error unpinning message: {e}")
        await update.message.reply_text("❌ Failed to unpin message. Make sure I have admin rights.")

@is_admin_command
@is_group_command
async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages between replied message and current message, or specified amount"""
    from config import Config
    
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text(
            "❌ Please reply to a message to purge from that point, or specify a number of messages to delete."
        )
        return
    
    try:
        chat_id = update.effective_chat.id
        current_message_id = update.message.message_id
        
        if context.args and context.args[0].isdigit():
            # Purge specified number of messages
            amount = min(int(context.args[0]), Config.PURGE_LIMIT)
            messages_to_delete = []
            
            for i in range(1, amount + 1):
                messages_to_delete.append(current_message_id - i)
            
        elif update.message.reply_to_message:
            # Purge from replied message to current
            start_id = update.message.reply_to_message.message_id
            messages_to_delete = list(range(start_id, current_message_id))
            
            if len(messages_to_delete) > Config.PURGE_LIMIT:
                await update.message.reply_text(
                    f"❌ Too many messages to delete (max {Config.PURGE_LIMIT}). "
                    f"Found {len(messages_to_delete)} messages."
                )
                return
        else:
            return
        
        # Delete messages
        deleted_count = 0
        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id, msg_id)
                deleted_count += 1
            except Exception:
                pass  # Message might already be deleted or too old
        
        # Delete the purge command message
        try:
            await context.bot.delete_message(chat_id, current_message_id)
        except Exception:
            pass
        
        # Send confirmation (will be auto-deleted after 5 seconds)
        if deleted_count > 0:
            confirmation = await context.bot.send_message(
                chat_id,
                f"🗑️ Purged {deleted_count} messages."
            )
            
            # Schedule deletion of confirmation message
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat_id, confirmation.message_id),
                5
            )
        
    except Exception as e:
        logger.error(f"Error purging messages: {e}")
        await update.message.reply_text("❌ Failed to purge messages. Make sure I have admin rights.")