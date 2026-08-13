from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command, get_user_from_message, format_user_mention
import logging

logger = logging.getLogger(__name__)

@is_admin_command
@is_group_command
async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Whitelist user so they bypass filters"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to whitelist (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if user_id:
        if db.add_whitelist(user_id, chat_id, admin_id):
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"✅ {user_mention} has been whitelisted in this chat!\n"
                f"They will now bypass all filters and restrictions.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User is already whitelisted in this chat.")

@is_admin_command
async def gwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally whitelist a user across all bot chats"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to globally whitelist (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    admin_id = update.effective_user.id
    
    if user_id:
        if db.add_whitelist(user_id, 0, admin_id, is_global=True):
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"🌐 {user_mention} has been globally whitelisted!\n"
                f"They will now bypass all filters and restrictions in all bot chats.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User is already globally whitelisted.")

@is_admin_command
@is_group_command
async def unwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from the whitelist"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to remove from whitelist (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        if db.remove_whitelist(user_id, chat_id):
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"✅ {user_mention} has been removed from the whitelist!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User is not whitelisted in this chat.")

@is_admin_command
async def gunwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from the global whitelist"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to remove from global whitelist (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    
    if user_id:
        if db.remove_whitelist(user_id, is_global=True):
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"🌐 {user_mention} has been removed from the global whitelist!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User is not globally whitelisted.")

@is_admin_command
@is_group_command
async def whitelisted_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a list of whitelisted users"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        whitelisted = session.query(db.Whitelist).filter(
            (db.Whitelist.chat_id == chat_id) | (db.Whitelist.is_global == True)
        ).order_by(db.Whitelist.created_at.desc()).limit(20).all()
        
        if not whitelisted:
            await update.message.reply_text("📋 No whitelisted users found.")
            return
        
        whitelist_msg = "📋 **Whitelisted Users:**\n\n"
        for entry in whitelisted:
            whitelist_type = "🌐 Global" if entry.is_global else "🏠 Local"
            whitelist_msg += f"{whitelist_type} • User ID: `{entry.user_id}`\n"
            whitelist_msg += f"   Added: {entry.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await update.message.reply_text(whitelist_msg, parse_mode='Markdown')
        
    finally:
        session.close()

@is_admin_command
@is_group_command
async def checkwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if a user is whitelisted"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to check whitelist status (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        is_whitelisted = db.is_whitelisted(user_id, chat_id)
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        
        if is_whitelisted:
            # Check if global or local
            session = db.get_session()
            try:
                global_whitelist = session.query(db.Whitelist).filter(
                    db.Whitelist.user_id == user_id,
                    db.Whitelist.is_global == True
                ).first()
                
                local_whitelist = session.query(db.Whitelist).filter(
                    db.Whitelist.user_id == user_id,
                    db.Whitelist.chat_id == chat_id
                ).first()
                
                status_msg = f"✅ {user_mention} is whitelisted!\n\n"
                
                if global_whitelist:
                    status_msg += "🌐 **Global whitelist** - bypasses filters in all chats\n"
                    status_msg += f"Added: {global_whitelist.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                
                if local_whitelist:
                    status_msg += "🏠 **Local whitelist** - bypasses filters in this chat\n"
                    status_msg += f"Added: {local_whitelist.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                
                await update.message.reply_text(status_msg, parse_mode='Markdown')
                
            finally:
                session.close()
        else:
            await update.message.reply_text(
                f"❌ {user_mention} is not whitelisted.",
                parse_mode='Markdown'
            )