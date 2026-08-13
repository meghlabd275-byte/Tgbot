from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database import db
from utils import is_admin_command, is_group_command, get_user_from_message, format_user_mention
from config import Config
import logging

logger = logging.getLogger(__name__)

@is_admin_command
@is_group_command
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Issue a warning to a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to warn (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    if user_id:
        # Add warning to database
        db.add_warning(user_id, chat_id, admin_id, reason)
        
        # Get current warning count
        warning_count = db.get_warnings_count(user_id, chat_id)
        
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        
        warning_msg = (
            f"⚠️ {user_mention} has been warned!\n"
            f"**Reason:** {reason}\n"
            f"**Warnings:** {warning_count}/{Config.MAX_WARNINGS}"
        )
        
        # Check if user should be banned for too many warnings
        if warning_count >= Config.MAX_WARNINGS:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                db.add_ban(user_id, chat_id, admin_id, f"Exceeded warning limit ({Config.MAX_WARNINGS} warnings)")
                warning_msg += f"\n\n🔨 **User has been banned for exceeding the warning limit!**"
            except BadRequest as e:
                warning_msg += f"\n\n❌ **Failed to auto-ban user: {e}**"
        
        await update.message.reply_text(warning_msg, parse_mode='Markdown')

@is_admin_command
async def gwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally issue a warning to a user across all bot chats"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to globally warn (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Global warning"
    
    if user_id:
        # Add global warning
        db.add_warning(user_id, 0, admin_id, reason, is_global=True)
        
        # Get total warning count across all chats
        session = db.get_session()
        try:
            total_warnings = session.query(db.Warning).filter(
                db.Warning.user_id == user_id
            ).count()
        finally:
            session.close()
        
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        
        await update.message.reply_text(
            f"🌐 {user_mention} has been globally warned!\n"
            f"**Reason:** {reason}\n"
            f"**Total warnings:** {total_warnings}",
            parse_mode='Markdown'
        )

@is_admin_command
@is_group_command
async def swarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently warn a user without an output message"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Silent warning"
    
    if user_id:
        # Add warning
        db.add_warning(user_id, chat_id, admin_id, reason)
        
        # Check if user should be banned
        warning_count = db.get_warnings_count(user_id, chat_id)
        if warning_count >= Config.MAX_WARNINGS:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                db.add_ban(user_id, chat_id, admin_id, f"Exceeded warning limit ({Config.MAX_WARNINGS} warnings)")
            except BadRequest:
                pass
        
        # Delete command message
        try:
            await context.bot.delete_message(chat_id, update.message.message_id)
        except:
            pass

@is_admin_command
@is_group_command
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a warning from the user's warning count"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to remove warning from (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        if db.remove_warning(user_id, chat_id):
            warning_count = db.get_warnings_count(user_id, chat_id)
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            
            await update.message.reply_text(
                f"✅ Removed one warning from {user_mention}!\n"
                f"**Current warnings:** {warning_count}/{Config.MAX_WARNINGS}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User has no warnings to remove.")

@is_admin_command
@is_group_command
async def resetwarns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completely wipe any warnings a user has"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to reset warnings for (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        removed_count = db.reset_warnings(user_id, chat_id)
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        
        if removed_count > 0:
            await update.message.reply_text(
                f"✅ Reset all warnings for {user_mention}!\n"
                f"**Removed {removed_count} warnings**",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"ℹ️ {user_mention} has no warnings to reset.", parse_mode='Markdown')

@is_admin_command
@is_group_command
async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check warning count for a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to check warnings for (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        warning_count = db.get_warnings_count(user_id, chat_id)
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        
        # Get recent warnings
        session = db.get_session()
        try:
            recent_warnings = session.query(db.Warning).filter(
                db.Warning.user_id == user_id,
                (db.Warning.chat_id == chat_id) | (db.Warning.is_global == True)
            ).order_by(db.Warning.created_at.desc()).limit(5).all()
            
            warning_msg = (
                f"⚠️ **Warning Status for {user_mention}**\n\n"
                f"**Current warnings:** {warning_count}/{Config.MAX_WARNINGS}\n"
            )
            
            if recent_warnings:
                warning_msg += "\n**Recent warnings:**\n"
                for warning in recent_warnings:
                    warning_type = "🌐 Global" if warning.is_global else "🏠 Local"
                    warning_msg += f"{warning_type} • {warning.reason}\n"
                    warning_msg += f"   Date: {warning.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                warning_msg += "\n✅ No warnings found!"
            
            await update.message.reply_text(warning_msg, parse_mode='Markdown')
            
        finally:
            session.close()