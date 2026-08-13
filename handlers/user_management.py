from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest
from database import db
from utils import (
    is_admin_command, is_group_command, get_user_from_message, 
    format_user_mention, parse_time_string, format_time_duration
)
from config import Config
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@is_admin_command
@is_group_command
async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to promote (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        # Add to database
        if db.add_admin(user_id, chat_id):
            # Try to promote in Telegram
            try:
                await context.bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_delete_messages=True,
                    can_restrict_members=True,
                    can_pin_messages=True,
                    can_promote_members=False
                )
                
                user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
                await update.message.reply_text(f"✅ {user_mention} has been promoted to admin!", parse_mode='Markdown')
            except BadRequest as e:
                await update.message.reply_text(f"⚠️ Added to bot admin list, but couldn't promote in Telegram: {e}")
        else:
            await update.message.reply_text("❌ User is already an admin.")

@is_admin_command
@is_group_command
async def title_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set admin title for a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user (reply to message, @username, or user ID).")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Please provide a title. Usage: /title @user Title Here")
        return
    
    user_id, user_obj = user_info
    title = ' '.join(context.args[1:]) if context.args[0].startswith('@') or context.args[0].isdigit() else ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    if user_id:
        try:
            await context.bot.set_chat_administrator_custom_title(
                chat_id=chat_id,
                user_id=user_id,
                custom_title=title
            )
            
            # Update in database
            session = db.get_session()
            try:
                admin = session.query(db.Admin).filter(
                    db.Admin.user_id == user_id,
                    db.Admin.chat_id == chat_id
                ).first()
                if admin:
                    admin.title = title
                    session.commit()
            finally:
                session.close()
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(f"✅ Set title '{title}' for {user_mention}!", parse_mode='Markdown')
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to set title: {e}")

@is_admin_command
@is_group_command
async def demote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote a user from admin"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to demote (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        # Remove from database
        if db.remove_admin(user_id, chat_id):
            # Try to demote in Telegram
            try:
                await context.bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False
                )
                
                user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
                await update.message.reply_text(f"✅ {user_mention} has been demoted from admin!", parse_mode='Markdown')
            except BadRequest as e:
                await update.message.reply_text(f"⚠️ Removed from bot admin list, but couldn't demote in Telegram: {e}")
        else:
            await update.message.reply_text("❌ User is not an admin.")

@is_admin_command
@is_group_command
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the chat"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to ban (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    if user_id:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            
            # Add to database
            db.add_ban(user_id, chat_id, admin_id, reason)
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"🔨 {user_mention} has been banned!\n"
                f"**Reason:** {reason}",
                parse_mode='Markdown'
            )
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to ban user: {e}")

@is_admin_command
@is_group_command
async def sban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently ban a user from the chat"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        return  # Silent command, no error message
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Silent ban"
    
    if user_id:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            db.add_ban(user_id, chat_id, admin_id, reason)
            
            # Delete the command message
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
                
        except BadRequest:
            pass  # Silent command, no error message

@is_admin_command
async def gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally ban a user from all bot chats"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to globally ban (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Global ban"
    
    if user_id:
        # Add global ban to database
        db.add_ban(user_id, 0, admin_id, reason, is_global=True)
        
        # Try to ban from all registered chats
        session = db.get_session()
        banned_chats = 0
        try:
            chats = session.query(db.Chat).all()
            for chat in chats:
                try:
                    await context.bot.ban_chat_member(chat.id, user_id)
                    banned_chats += 1
                except:
                    pass  # Chat might be inactive or bot removed
        finally:
            session.close()
        
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        await update.message.reply_text(
            f"🌐 {user_mention} has been globally banned!\n"
            f"**Reason:** {reason}\n"
            f"**Banned from {banned_chats} chats**",
            parse_mode='Markdown'
        )

@is_admin_command
async def sgban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently globally ban a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        return
    
    user_id, user_obj = user_info
    admin_id = update.effective_user.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Silent global ban"
    
    if user_id:
        db.add_ban(user_id, 0, admin_id, reason, is_global=True)
        
        # Ban from all chats silently
        session = db.get_session()
        try:
            chats = session.query(db.Chat).all()
            for chat in chats:
                try:
                    await context.bot.ban_chat_member(chat.id, user_id)
                except:
                    pass
        finally:
            session.close()
        
        # Delete command message
        try:
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
        except:
            pass

@is_admin_command
@is_group_command
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the chat"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to unban (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        try:
            await context.bot.unban_chat_member(chat_id, user_id)
            
            # Remove from database
            db.remove_ban(user_id, chat_id)
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(f"✅ {user_mention} has been unbanned!", parse_mode='Markdown')
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to unban user: {e}")

@is_admin_command
async def gunban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally unban a user from all bot chats"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to globally unban (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    
    if user_id:
        # Remove global ban from database
        if db.remove_ban(user_id, is_global=True):
            # Unban from all chats
            session = db.get_session()
            unbanned_chats = 0
            try:
                chats = session.query(db.Chat).all()
                for chat in chats:
                    try:
                        await context.bot.unban_chat_member(chat.id, user_id)
                        unbanned_chats += 1
                    except:
                        pass
            finally:
                session.close()
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"🌐 {user_mention} has been globally unbanned!\n"
                f"**Unbanned from {unbanned_chats} chats**",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ User is not globally banned.")

@is_admin_command
@is_group_command
async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View list of banned users"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        bans = session.query(db.Ban).filter(
            (db.Ban.chat_id == chat_id) | (db.Ban.is_global == True)
        ).order_by(db.Ban.created_at.desc()).limit(20).all()
        
        if not bans:
            await update.message.reply_text("📋 No banned users found.")
            return
        
        ban_list = "📋 **Banned Users:**\n\n"
        for ban in bans:
            ban_type = "🌐 Global" if ban.is_global else "🏠 Local"
            ban_list += f"{ban_type} • User ID: `{ban.user_id}`\n"
            if ban.reason:
                ban_list += f"   Reason: {ban.reason}\n"
            ban_list += f"   Date: {ban.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await update.message.reply_text(ban_list, parse_mode='Markdown')
        
    finally:
        session.close()

@is_admin_command
@is_group_command
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the chat"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to kick (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    if user_id:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"👢 {user_mention} has been kicked!\n"
                f"**Reason:** {reason}",
                parse_mode='Markdown'
            )
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to kick user: {e}")

@is_admin_command
@is_group_command
async def skick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently kick a user from the chat"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            
            # Delete command message
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
                
        except BadRequest:
            pass

@is_admin_command
async def gkick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Globally kick a user from all chats"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to globally kick (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Global kick"
    
    if user_id:
        session = db.get_session()
        kicked_chats = 0
        try:
            chats = session.query(db.Chat).all()
            for chat in chats:
                try:
                    await context.bot.ban_chat_member(chat.id, user_id)
                    await context.bot.unban_chat_member(chat.id, user_id)
                    kicked_chats += 1
                except:
                    pass
        finally:
            session.close()
        
        user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
        await update.message.reply_text(
            f"🌐 {user_mention} has been globally kicked!\n"
            f"**Reason:** {reason}\n"
            f"**Kicked from {kicked_chats} chats**",
            parse_mode='Markdown'
        )

@is_admin_command
@is_group_command
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user for a specified time"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to mute (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    # Parse duration and reason
    duration = Config.DEFAULT_MUTE_TIME
    reason = "No reason provided"
    
    if context.args:
        if len(context.args) >= 2:
            duration = parse_time_string(context.args[1])
            reason = ' '.join(context.args[2:]) if len(context.args) > 2 else reason
        elif len(context.args) == 1 and not context.args[0].startswith('@') and not context.args[0].isdigit():
            duration = parse_time_string(context.args[0])
    
    if user_id:
        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=context.bot.get_chat(chat_id).permissions,
                until_date=until_date
            )
            
            # Add to database
            db.add_mute(user_id, chat_id, admin_id, duration, reason)
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(
                f"🔇 {user_mention} has been muted for {format_time_duration(duration)}!\n"
                f"**Reason:** {reason}",
                parse_mode='Markdown'
            )
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to mute user: {e}")

@is_admin_command
@is_group_command
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        await update.message.reply_text("❌ Please specify a user to unmute (reply to message, @username, or user ID).")
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    
    if user_id:
        try:
            # Get chat permissions
            chat = await context.bot.get_chat(chat_id)
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=chat.permissions
            )
            
            # Remove from database
            db.remove_mute(user_id, chat_id)
            
            user_mention = format_user_mention(user_obj) if user_obj else f"User {user_id}"
            await update.message.reply_text(f"🔊 {user_mention} has been unmuted!", parse_mode='Markdown')
            
        except BadRequest as e:
            await update.message.reply_text(f"❌ Failed to unmute user: {e}")

@is_admin_command
@is_group_command
async def smute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently mute a user"""
    user_info = get_user_from_message(update, context)
    if not user_info:
        return
    
    user_id, user_obj = user_info
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    duration = Config.DEFAULT_MUTE_TIME
    if context.args and len(context.args) >= 2:
        duration = parse_time_string(context.args[1])
    
    if user_id:
        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=context.bot.get_chat(chat_id).permissions,
                until_date=until_date
            )
            
            db.add_mute(user_id, chat_id, admin_id, duration, "Silent mute")
            
            # Delete command message
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
                
        except BadRequest:
            pass