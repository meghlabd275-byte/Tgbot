from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from database import db
from utils import (
    is_admin_command, is_group_command, get_file_id_from_message,
    get_telegram_admins, sync_telegram_admins,
)
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

@is_admin_command
@is_group_command
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register the current chat and sync all of its admins into the bot."""
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

    # Register chat, user, and ALL current Telegram admins of the chat so any
    # admin of this group can manage the bot (multi-admin support).
    db.get_or_create_chat(chat.id, chat.title)
    db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    await sync_telegram_admins(context, chat.id)

    admin_count = len(db.get_chat_admins(chat.id))

    await update.message.reply_text(
        f"✅ Chat **{chat.title}** has been activated!\n"
        f"📋 **{admin_count} admin(s)** registered for this group.\n"
        "Any group admin can now configure and use the bot in this chat.",
        parse_mode='Markdown'
    )


async def adminlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List the group's admins (usable by anyone, mirrors Rose's /adminlist)."""
    chat_id = update.effective_chat.id
    # Prefer the live Telegram admin list, fall back to the bot's local DB.
    admins = await get_telegram_admins(context, chat_id)

    if admins is None:
        session = db.get_session()
        try:
            rows = session.query(db.Admin).filter(db.Admin.chat_id == chat_id).all()
            ids = [r.user_id for r in rows]
        finally:
            session.close()
        if not ids:
            await update.message.reply_text("👥 Could not retrieve the admin list.")
            return
        msg = "👥 **Group Admins:**\n\n"
        for uid in ids:
            msg += f"• `{uid}`\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    msg = f"👥 **Group Admins ({len(admins)}):**\n\n"
    for admin in admins:
        name = admin.first_name
        if admin.last_name:
            name += f" {admin.last_name}"
        mention = f"@{admin.username}" if admin.username else name
        icon = "🤖 " if admin.id == context.bot.id else "• "
        msg += f"{icon}{mention} — `{admin.id}`\n"
    await update.message.reply_text(msg, parse_mode='Markdown')


@is_admin_command
@is_group_command
async def warnmode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View or set how the bot reacts when a user hits the warning limit."""
    from handlers.moderation import VALID_WARN_MODES, set_warn_mode_command_response

    chat_id = update.effective_chat.id

    if not context.args:
        settings = db.get_warn_settings(chat_id)
        await update.message.reply_text(
            f"⚠️ **Warn Mode: {settings['mode']}**\n"
            f"**Warning limit:** {settings['limit']}\n\n"
            f"Available modes: {', '.join(VALID_WARN_MODES)}\n"
            "Usage: `/warnmode <kick|ban|mute|tban>`",
            parse_mode='Markdown',
        )
        return

    mode = context.args[0].lower().strip()
    if mode not in VALID_WARN_MODES:
        await update.message.reply_text(
            f"❌ Invalid warn mode. Use: {', '.join(VALID_WARN_MODES)}"
        )
        return

    response = set_warn_mode_command_response(chat_id, mode)
    await update.message.reply_text(response, parse_mode='Markdown')


@is_admin_command
@is_group_command
async def silence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silence the chat - only admins can speak"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat:
            if chat.is_silenced:
                await update.message.reply_text("🔇 Chat is already silenced.")
                return
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
    """Reload admin cache and resync all current Telegram admins into the DB"""
    from utils import update_chat_admins_cache

    chat_id = update.effective_chat.id
    success = await update_chat_admins_cache(context, chat_id)
    # Also resync the persistent admin DB so any Telegram admin works.
    await sync_telegram_admins(context, chat_id)
    
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
        # `/pin` -> notify; `/pin silent` / `/pin quiet` -> pin without notification.
        arg = (context.args[0].lower() if context.args else '')
        disable_notification = arg in ('silent', 'quiet', 'loudless')

        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=message_to_pin.message_id,
            disable_notification=disable_notification
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
            value = int(context.args[0])
            # A number larger than the purge limit is treated as a starting
            # message ID (delete from that ID up to the current message);
            # otherwise it is the number of messages to delete.
            if value > Config.PURGE_LIMIT:
                messages_to_delete = list(range(value, current_message_id))
                if len(messages_to_delete) > Config.PURGE_LIMIT:
                    await update.message.reply_text(
                        f"❌ Too many messages to delete (max {Config.PURGE_LIMIT}). "
                        f"Found {len(messages_to_delete)} messages."
                    )
                    return
            else:
                messages_to_delete = []
                for i in range(1, value + 1):
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

@is_admin_command
@is_group_command
async def del_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the replied-to message (Rose-style /del)."""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to delete it.")
        return

    chat_id = update.effective_chat.id
    try:
        await context.bot.delete_message(chat_id, update.message.reply_to_message.message_id)
        try:
            await update.message.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        await update.message.reply_text("❌ Failed to delete that message. Check my admin rights.")

@is_admin_command
@is_group_command
async def spurge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently purge messages between the replied message and now (Rose-style /spurge)."""
    from config import Config

    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("❌ Reply to a message to purge from that point, or specify a number.")
        return

    chat_id = update.effective_chat.id
    current_message_id = update.message.message_id

    if context.args and context.args[0].isdigit():
        amount = min(int(context.args[0]), Config.PURGE_LIMIT)
        messages_to_delete = [current_message_id - i for i in range(1, amount + 1)]
    elif update.message.reply_to_message:
        start_id = update.message.reply_to_message.message_id
        messages_to_delete = list(range(start_id, current_message_id))
        if len(messages_to_delete) > Config.PURGE_LIMIT:
            await update.message.reply_text(
                f"❌ Too many messages to delete (max {Config.PURGE_LIMIT})."
            )
            return
    else:
        return

    deleted_count = 0
    for msg_id in messages_to_delete:
        try:
            await context.bot.delete_message(chat_id, msg_id)
            deleted_count += 1
        except Exception:
            pass

    # Also delete the command itself, and send NO confirmation (silent).
    try:
        await context.bot.delete_message(chat_id, current_message_id)
    except Exception:
        pass
