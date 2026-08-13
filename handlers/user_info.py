from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, get_user_from_message, format_user_mention
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@is_admin_command
async def resetuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove bans, warns, mutes for a user in your channel"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to reset (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        session = db.get_session()
        try:
            # Remove bans
            bans_removed = session.query(db.Ban).filter(
                db.Ban.user_id == user_id,
                db.Ban.chat_id == chat_id
            ).delete()
            
            # Remove warnings
            warnings_removed = session.query(db.Warning).filter(
                db.Warning.user_id == user_id,
                db.Warning.chat_id == chat_id
            ).delete()
            
            # Remove mutes
            mutes_removed = session.query(db.Mute).filter(
                db.Mute.user_id == user_id,
                db.Mute.chat_id == chat_id
            ).delete()
            
            session.commit()
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            
            reset_msg = f"✅ **User reset completed for {user_mention}**\n\n"
            reset_msg += f"🔨 Bans removed: {bans_removed}\n"
            reset_msg += f"⚠️ Warnings removed: {warnings_removed}\n"
            reset_msg += f"🔇 Mutes removed: {mutes_removed}\n"
            
            # Try to unban/unmute in Telegram
            try:
                await context.bot.unban_chat_member(chat_id, user_id)
                reset_msg += "\n✅ User unbanned in Telegram"
            except:
                pass
            
            try:
                chat = await context.bot.get_chat(chat_id)
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=chat.permissions
                )
                reset_msg += "\n✅ User unmuted in Telegram"
            except:
                pass
            
            await update.message.reply_text(reset_msg, parse_mode='Markdown')
            
        finally:
            session.close()

@is_admin_command
async def resetrep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset a user's reputation to 0"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to reset reputation for (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    
    if user_id:
        session = db.get_session()
        try:
            user = session.query(db.User).filter(db.User.id == user_id).first()
            if user:
                old_rep = user.reputation
                user.reputation = 0
                session.commit()
                
                user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
                await update.message.reply_text(
                    f"✅ Reset reputation for {user_mention}\n"
                    f"**Previous reputation:** {old_rep}\n"
                    f"**New reputation:** 0",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ User not found in database.")
        finally:
            session.close()

async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View information about a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        # If no user specified, show info about the command sender
        user_id = update.effective_user.id
        user_obj = update.effective_user
    else:
        user_id, user_obj = user_info
    
    if user_id:
        chat_id = update.effective_chat.id
        session = db.get_session()
        try:
            # Get user from database
            db_user = session.query(db.User).filter(db.User.id == user_id).first()
            
            # Get user stats
            warning_count = session.query(db.Warning).filter(
                db.Warning.user_id == user_id,
                (db.Warning.chat_id == chat_id) | (db.Warning.is_global == True)
            ).count()
            
            is_banned = session.query(db.Ban).filter(
                db.Ban.user_id == user_id,
                (db.Ban.chat_id == chat_id) | (db.Ban.is_global == True)
            ).first() is not None
            
            is_muted = session.query(db.Mute).filter(
                db.Mute.user_id == user_id,
                db.Mute.chat_id == chat_id,
                db.Mute.until > datetime.now()
            ).first() is not None
            
            is_whitelisted = session.query(db.Whitelist).filter(
                db.Whitelist.user_id == user_id,
                (db.Whitelist.chat_id == chat_id) | (db.Whitelist.is_global == True)
            ).first() is not None
            
            is_admin = db.is_admin(user_id, chat_id)
            
            # Format user info
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            
            user_info_msg = f"👤 **User Information**\n\n"
            user_info_msg += f"**User:** {user_mention}\n"
            user_info_msg += f"**ID:** `{user_id}`\n"
            
            if user_obj:
                if user_obj.username:
                    user_info_msg += f"**Username:** @{user_obj.username}\n"
                user_info_msg += f"**Name:** {user_obj.first_name}"
                if user_obj.last_name:
                    user_info_msg += f" {user_obj.last_name}"
                user_info_msg += "\n"
            
            if db_user:
                user_info_msg += f"**Reputation:** {db_user.reputation}\n"
                user_info_msg += f"**Last Active:** {db_user.last_active.strftime('%Y-%m-%d %H:%M')}\n"
                user_info_msg += f"**Registered:** {db_user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            
            user_info_msg += f"\n**Status:**\n"
            user_info_msg += f"• Admin: {'✅' if is_admin else '❌'}\n"
            user_info_msg += f"• Banned: {'✅' if is_banned else '❌'}\n"
            user_info_msg += f"• Muted: {'✅' if is_muted else '❌'}\n"
            user_info_msg += f"• Whitelisted: {'✅' if is_whitelisted else '❌'}\n"
            user_info_msg += f"• Warnings: {warning_count}\n"
            
            await update.message.reply_text(user_info_msg, parse_mode='Markdown')
            
        finally:
            session.close()

@is_admin_command
async def lastactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the last active date of a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to check last active date (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    
    if user_id:
        session = db.get_session()
        try:
            user = session.query(db.User).filter(db.User.id == user_id).first()
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            
            if user and user.last_active:
                time_diff = datetime.now() - user.last_active
                
                if time_diff.days > 0:
                    time_str = f"{time_diff.days} days ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_str = f"{hours} hours ago"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    time_str = f"{minutes} minutes ago"
                else:
                    time_str = "Just now"
                
                await update.message.reply_text(
                    f"🕐 **Last Active for {user_mention}**\n\n"
                    f"**Date:** {user.last_active.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Time ago:** {time_str}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ No activity data found for {user_mention}",
                    parse_mode='Markdown'
                )
        finally:
            session.close()

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user or chat ID"""
    if update.message.reply_to_message:
        # Get ID of replied user
        replied_user = update.message.reply_to_message.from_user
        await update.message.reply_text(
            f"👤 **User ID:** `{replied_user.id}`\n"
            f"💬 **Chat ID:** `{update.effective_chat.id}`",
            parse_mode='Markdown'
        )
    else:
        # Get ID of command sender and chat
        await update.message.reply_text(
            f"👤 **Your ID:** `{update.effective_user.id}`\n"
            f"💬 **Chat ID:** `{update.effective_chat.id}`",
            parse_mode='Markdown'
        )

async def chatinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get information about the current chat"""
    chat = update.effective_chat
    
    session = db.get_session()
    try:
        db_chat = session.query(db.Chat).filter(db.Chat.id == chat.id).first()
        
        # Count members (if possible)
        member_count = "Unknown"
        try:
            member_count = await context.bot.get_chat_member_count(chat.id)
        except:
            pass
        
        # Count admins in database
        admin_count = session.query(db.Admin).filter(db.Admin.chat_id == chat.id).count()
        
        # Count banned users
        ban_count = session.query(db.Ban).filter(
            (db.Ban.chat_id == chat.id) | (db.Ban.is_global == True)
        ).count()
        
        chat_info_msg = f"💬 **Chat Information**\n\n"
        chat_info_msg += f"**Name:** {chat.title or 'N/A'}\n"
        chat_info_msg += f"**ID:** `{chat.id}`\n"
        chat_info_msg += f"**Type:** {chat.type}\n"
        chat_info_msg += f"**Members:** {member_count}\n"
        
        if db_chat:
            chat_info_msg += f"**Registered:** ✅\n"
            chat_info_msg += f"**Silenced:** {'✅' if db_chat.is_silenced else '❌'}\n"
            chat_info_msg += f"**Under Attack:** {'✅' if db_chat.under_attack else '❌'}\n"
            chat_info_msg += f"**Created:** {db_chat.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        else:
            chat_info_msg += f"**Registered:** ❌\n"
        
        chat_info_msg += f"\n**Statistics:**\n"
        chat_info_msg += f"• Bot Admins: {admin_count}\n"
        chat_info_msg += f"• Banned Users: {ban_count}\n"
        
        await update.message.reply_text(chat_info_msg, parse_mode='Markdown')
        
    finally:
        session.close()