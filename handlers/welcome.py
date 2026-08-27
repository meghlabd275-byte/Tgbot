from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command, format_user_mention
import logging

logger = logging.getLogger(__name__)

# Add new tables for welcome system
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base

class WelcomeSettings(Base):
    __tablename__ = 'welcome_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    welcome_enabled = Column(Boolean, default=True)
    goodbye_enabled = Column(Boolean, default=False)
    welcome_message = Column(Text)
    goodbye_message = Column(Text)
    welcome_media = Column(String(255))  # file_id for photo/video
    media_type = Column(String(50))  # photo, video, gif
    delete_welcome = Column(Integer, default=0)  # seconds to delete welcome message
    delete_service = Column(Boolean, default=False)  # delete all service messages (legacy master toggle)
    # Granular Join-Hider controls (like @joinhider_bot)
    delete_joined_msg = Column(Boolean, default=False)  # delete "X joined" service messages
    delete_left_msg = Column(Boolean, default=False)     # delete "X left" service messages
    delete_all_system_msg = Column(Boolean, default=False)  # delete ALL service messages (pin, title, photo, group created, etc.)
    welcome_buttons = Column(Text)  # JSON string for buttons
    captcha_enabled = Column(Boolean, default=False)
    captcha_time = Column(Integer, default=300)  # 5 minutes
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class PendingUsers(Base):
    __tablename__ = 'pending_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    user_id = Column(BigInteger)
    join_time = Column(DateTime, default=func.now())
    captcha_message_id = Column(Integer)

def update_welcome_database():
    from database import db as database_instance
    Base.metadata.create_all(bind=database_instance.engine)

@is_admin_command
@is_group_command
async def setwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set welcome message"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/setwelcome <message>`\n\n"
            "**Variables you can use:**\n"
            "• `{first}` - User's first name\n"
            "• `{last}` - User's last name\n"
            "• `{fullname}` - User's full name\n"
            "• `{username}` - User's username\n"
            "• `{mention}` - Mention the user\n"
            "• `{id}` - User's ID\n"
            "• `{chatname}` - Chat name\n"
            "• `{count}` - Member count\n\n"
            "**Example:**\n"
            "`/setwelcome Welcome {mention} to {chatname}! We now have {count} members.`",
            parse_mode='Markdown'
        )
        return
    
    welcome_text = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if settings:
            settings.welcome_message = welcome_text
            settings.welcome_enabled = True
            session.commit()
        else:
            settings = WelcomeSettings(
                chat_id=chat_id,
                welcome_message=welcome_text,
                welcome_enabled=True
            )
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(
            f"✅ Welcome message set!\n\n**Preview:**\n{format_welcome_message(welcome_text, update.effective_user, update.effective_chat)}",
            parse_mode='Markdown'
        )
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def setgoodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set goodbye message"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/setgoodbye <message>`\n\n"
            "Same variables as welcome message can be used.",
            parse_mode='Markdown'
        )
        return
    
    goodbye_text = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if settings:
            settings.goodbye_message = goodbye_text
            settings.goodbye_enabled = True
            session.commit()
        else:
            settings = WelcomeSettings(
                chat_id=chat_id,
                goodbye_message=goodbye_text,
                goodbye_enabled=True
            )
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(
            f"✅ Goodbye message set!\n\n**Preview:**\n{format_welcome_message(goodbye_text, update.effective_user, update.effective_chat)}",
            parse_mode='Markdown'
        )
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle welcome messages or show settings"""
    if not context.args:
        # Show current settings
        chat_id = update.effective_chat.id
        session = db.get_session()
        try:
            settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
            
            if not settings:
                await update.message.reply_text("❌ No welcome settings configured. Use `/setwelcome` to set up.")
                return
            
            welcome_info = f"""👋 **Welcome Settings**

**Welcome:** {'✅ Enabled' if settings.welcome_enabled else '❌ Disabled'}
**Goodbye:** {'✅ Enabled' if settings.goodbye_enabled else '❌ Disabled'}
**Captcha:** {'✅ Enabled' if settings.captcha_enabled else '❌ Disabled'}
**Delete Service Messages:** {'✅ Yes' if settings.delete_service else '❌ No'}

**Welcome Message:**
{settings.welcome_message or 'Not set'}

**Goodbye Message:**
{settings.goodbye_message or 'Not set'}

**Commands:**
• `/welcome on|off` - Toggle welcome
• `/goodbye on|off` - Toggle goodbye
• `/setwelcome <text>` - Set welcome message
• `/setgoodbye <text>` - Set goodbye message
• `/captcha on|off` - Toggle captcha
• `/cleanservice on|off` - Toggle service message deletion"""
            
            await update.message.reply_text(welcome_info, parse_mode='Markdown')
        
        finally:
            session.close()
        return
    
    # Toggle welcome
    if context.args[0].lower() in ['on', 'off']:
        status = context.args[0].lower() == 'on'
        chat_id = update.effective_chat.id
        
        session = db.get_session()
        try:
            settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
            
            if settings:
                settings.welcome_enabled = status
                session.commit()
            else:
                settings = WelcomeSettings(chat_id=chat_id, welcome_enabled=status)
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"✅ Welcome messages {'enabled' if status else 'disabled'}.")
        
        finally:
            session.close()

@is_admin_command
@is_group_command
async def goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle goodbye messages"""
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("❌ Usage: `/goodbye on|off`")
        return
    
    status = context.args[0].lower() == 'on'
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if settings:
            settings.goodbye_enabled = status
            session.commit()
        else:
            settings = WelcomeSettings(chat_id=chat_id, goodbye_enabled=status)
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(f"✅ Goodbye messages {'enabled' if status else 'disabled'}.")
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def captcha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle captcha for new users"""
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("❌ Usage: `/captcha on|off`")
        return
    
    status = context.args[0].lower() == 'on'
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if settings:
            settings.captcha_enabled = status
            session.commit()
        else:
            settings = WelcomeSettings(chat_id=chat_id, captcha_enabled=status)
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(
            f"✅ Captcha {'enabled' if status else 'disabled'}.\n"
            f"{'New users will need to solve a captcha to chat.' if status else ''}"
        )
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def cleanservice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle deletion of service messages"""
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("❌ Usage: `/cleanservice on|off`")
        return
    
    status = context.args[0].lower() == 'on'
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if settings:
            settings.delete_service = status
            session.commit()
        else:
            settings = WelcomeSettings(chat_id=chat_id, delete_service=status)
            session.add(settings)
            session.commit()
        
        await update.message.reply_text(
            f"✅ Service message deletion {'enabled' if status else 'disabled'}.\n"
            f"{'Join/leave messages will be automatically deleted.' if status else ''}\n"
            f"💡 For granular control use `/joinhider` (separate joined/left toggles).",
            parse_mode='Markdown'
        )
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def joinhider_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Granular Join-Hider control (mirrors @joinhider_bot).

    Usage:
      /joinhider                          -> show current settings
      /joinhider joined on|off            -> delete "X joined" service messages
      /joinhider left on|off              -> delete "X left" service messages
      /joinhider all on|off               -> delete both joined + left messages
      /joinhider system on|off           -> delete ALL service messages (pins, title/photo
                                             changes, group created, etc.) — the
                                             delete_all_system_msg option from @joinhider_bot
    """
    chat_id = update.effective_chat.id
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        if not settings:
            settings = WelcomeSettings(chat_id=chat_id)
            session.add(settings)

        if not context.args:
            await update.message.reply_text(
                "🚪 **Join Hider** — hide system join/leave messages\n\n"
                f"• Delete joined messages: {'✅' if settings.delete_joined_msg else '❌'}\n"
                f"• Delete left messages: {'✅' if settings.delete_left_msg else '❌'}\n"
                f"• Delete ALL system messages: {'✅' if settings.delete_all_system_msg else '❌'}\n"
                f"• Delete all service (legacy): {'✅' if settings.delete_service else '❌'}\n\n"
                "**Commands:**\n"
                "• `/joinhider joined on|off` — hide \"X joined\" messages\n"
                "• `/joinhider left on|off` — hide \"X left\" messages\n"
                "• `/joinhider all on|off` — hide both join + leave\n"
                "• `/joinhider system on|off` — hide ALL service messages (pins, title/photo changes)\n"
                "• `/cleanservice on|off` — legacy master toggle",
                parse_mode='Markdown',
            )
            return

        sub = context.args[0].lower()

        def _bool(val: str) -> bool:
            return val.lower() in ('on', 'yes', 'true', '1')

        if sub == 'joined':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/joinhider joined on|off`", parse_mode='Markdown')
                return
            settings.delete_joined_msg = _bool(context.args[1])
            msg = f"✅ Hiding 'joined' messages {'enabled' if settings.delete_joined_msg else 'disabled'}."
        elif sub == 'left':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/joinhider left on|off`", parse_mode='Markdown')
                return
            settings.delete_left_msg = _bool(context.args[1])
            msg = f"✅ Hiding 'left' messages {'enabled' if settings.delete_left_msg else 'disabled'}."
        elif sub == 'all':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/joinhider all on|off`", parse_mode='Markdown')
                return
            val = _bool(context.args[1])
            settings.delete_joined_msg = val
            settings.delete_left_msg = val
            msg = f"✅ Hiding all join/leave messages {'enabled' if val else 'disabled'}."
        elif sub == 'system':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Usage: `/joinhider system on|off`", parse_mode='Markdown')
                return
            settings.delete_all_system_msg = _bool(context.args[1])
            msg = (f"✅ Hiding ALL system messages {'enabled' if settings.delete_all_system_msg else 'disabled'}.\n"
                   "Pinned-message, title-change, photo-change and group-created notifications will be deleted.")
        else:
            await update.message.reply_text(
                "❌ Unknown option. Use: joined, left, all, system", parse_mode='Markdown'
            )
            return

        session.commit()
        await update.message.reply_text(msg, parse_mode='Markdown')
    finally:
        session.close()

async def handle_new_member_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new member with welcome message and captcha, plus security checks"""
    chat_id = update.effective_chat.id
    new_members = update.message.new_chat_members or []

    # Anti-raid: track joins and auto-enable under-attack mode on a burst
    try:
        from handlers.antiflood import check_raid
        await check_raid(update, context)
    except Exception as e:
        logger.error(f"Raid check failed: {e}")

    # If the bot itself was added to the chat, register it and announce
    bot_user = context.bot
    bot_added = any(m.is_bot and m.id == bot_user.id for m in new_members)
    if bot_added:
        db.get_or_create_chat(chat_id, update.effective_chat.title)
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
            await context.bot.send_message(chat_id, welcome_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send bot-added welcome to chat {chat_id}: {e}")
        return

    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()

        # Security checks: under-attack auto-kick and global-ban enforcement
        chat_obj = session.query(db.Chat).filter(db.Chat.id == chat_id).first()
        if chat_obj and chat_obj.under_attack:
            for member in new_members:
                if member.is_bot:
                    continue
                try:
                    await context.bot.ban_chat_member(chat_id, member.id)
                    await context.bot.unban_chat_member(chat_id, member.id)
                    logger.info(f"Kicked new member {member.id} due to under-attack mode in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to kick new member {member.id}: {e}")
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
            return

        # Enforce global bans on join + register user
        for member in new_members:
            if member.is_bot:
                continue
            banned = db.is_banned(member.id)
            if banned:
                try:
                    await context.bot.ban_chat_member(chat_id, member.id)
                    logger.info(f"Banned new member {member.id} due to global ban in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to ban globally banned member {member.id}: {e}")
            else:
                db.get_or_create_user(member.id, member.username, member.first_name, member.last_name)

        # Enforce federation bans on join
        try:
            from handlers.federations import enforce_federation_bans
            await enforce_federation_bans(update, context)
        except Exception as e:
            logger.error(f"Federation ban enforcement failed: {e}")

        if not settings:
            return

        # Delete the "X joined" service message if any join-hider toggle is on.
        # delete_service is the legacy master toggle; delete_joined_msg is the
        # granular control (mirrors @joinhider_bot's delete_user_joined_msg).
        if settings.delete_service or settings.delete_joined_msg:
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
            # If we deleted the service message AND there is no welcome/captcha
            # to send, we're done (pure join-hider mode).
            if not (settings.welcome_enabled or settings.captcha_enabled):
                return

        for new_member in new_members:
            if new_member.is_bot:
                continue

            if settings.captcha_enabled:
                await handle_captcha(update, context, new_member, settings)
            elif settings.welcome_enabled and settings.welcome_message:
                await send_welcome_message(update, context, new_member, settings)

    finally:
        session.close()

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE, user, settings):
    """Handle captcha for new user"""
    import random
    
    chat_id = update.effective_chat.id
    user_id = user.id
    
    # Restrict user until captcha is solved
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
    except:
        pass
    
    # Generate simple math captcha
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    answer = num1 + num2
    
    # Create captcha buttons
    buttons = []
    correct_answer = answer
    wrong_answers = [answer + random.randint(1, 5), answer - random.randint(1, 5), answer + random.randint(6, 10)]
    
    all_answers = [correct_answer] + wrong_answers[:2]
    random.shuffle(all_answers)
    
    for ans in all_answers:
        buttons.append(InlineKeyboardButton(str(ans), callback_data=f"captcha_{user_id}_{ans}_{correct_answer}"))
    
    keyboard = InlineKeyboardMarkup([buttons])
    
    captcha_text = f"""🔐 **Captcha Verification**

Welcome {format_user_mention(user)}!

To prove you're human, please solve this simple math problem:
**{num1} + {num2} = ?**

You have {settings.captcha_time // 60} minutes to solve this, or you'll be kicked."""
    
    try:
        captcha_msg = await context.bot.send_message(
            chat_id,
            captcha_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Store pending user
        session = db.get_session()
        try:
            pending = PendingUsers(
                chat_id=chat_id,
                user_id=user_id,
                captcha_message_id=captcha_msg.message_id
            )
            session.add(pending)
            session.commit()
        finally:
            session.close()
        
        # Schedule kick if not solved
        context.job_queue.run_once(
            lambda context: kick_unverified_user(context, chat_id, user_id, captcha_msg.message_id),
            settings.captcha_time
        )
        
    except Exception as e:
        logger.error(f"Error sending captcha: {e}")

async def kick_unverified_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, message_id: int):
    """Kick user who didn't solve captcha"""
    session = db.get_session()
    try:
        pending = session.query(PendingUsers).filter(
            PendingUsers.chat_id == chat_id,
            PendingUsers.user_id == user_id
        ).first()
        
        if pending:
            # User still pending, kick them
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                await context.bot.delete_message(chat_id, message_id)
                
                await context.bot.send_message(
                    chat_id,
                    f"⏰ User kicked for not solving captcha in time."
                )
            except:
                pass
            
            session.delete(pending)
            session.commit()
    
    finally:
        session.close()

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user, settings):
    """Send welcome message to new user"""
    chat = update.effective_chat
    
    welcome_text = format_welcome_message(settings.welcome_message, user, chat)
    
    try:
        welcome_msg = await context.bot.send_message(
            chat.id,
            welcome_text,
            parse_mode='Markdown'
        )
        
        # Delete welcome message after specified time
        if settings.delete_welcome > 0:
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat.id, welcome_msg.message_id),
                settings.delete_welcome
            )
    
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

async def handle_left_member_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle member leaving with goodbye message"""
    chat_id = update.effective_chat.id
    left_member = update.message.left_chat_member
    
    if not left_member or left_member.is_bot:
        return
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if not settings:
            return
        
        # Delete the "X left" service message if any join-hider toggle is on.
        # delete_service is the legacy master toggle; delete_left_msg is the
        # granular control (mirrors @joinhider_bot's delete_user_left_msg).
        if settings.delete_service or settings.delete_left_msg:
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
            # Pure join-hider mode: if no goodbye to send, stop here.
            if not (settings.goodbye_enabled and settings.goodbye_message):
                return
        
        # Send goodbye message
        if settings.goodbye_enabled and settings.goodbye_message:
            goodbye_text = format_welcome_message(settings.goodbye_message, left_member, update.effective_chat)
            
            try:
                await context.bot.send_message(
                    chat_id,
                    goodbye_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending goodbye message: {e}")
    
    finally:
        session.close()

def format_welcome_message(template: str, user, chat) -> str:
    """Format welcome message with variables"""
    if not template:
        return ""
    
    # Get member count
    try:
        member_count = "many"  # We'll implement this properly
    except:
        member_count = "many"
    
    replacements = {
        '{first}': user.first_name or '',
        '{last}': user.last_name or '',
        '{fullname}': f"{user.first_name or ''} {user.last_name or ''}".strip(),
        '{username}': f"@{user.username}" if user.username else user.first_name,
        '{mention}': format_user_mention(user),
        '{id}': str(user.id),
        '{chatname}': chat.title or 'this chat',
        '{count}': str(member_count)
    }
    
    formatted = template
    for placeholder, value in replacements.items():
        formatted = formatted.replace(placeholder, value)
    
    return formatted

# Handle captcha button callbacks
async def handle_captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle captcha button press"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if len(data) != 4 or data[0] != 'captcha':
        return
    
    user_id = int(data[1])
    selected_answer = int(data[2])
    correct_answer = int(data[3])
    
    # Check if the user pressing the button is the one who needs to solve captcha
    if query.from_user.id != user_id:
        await query.answer("❌ This captcha is not for you!", show_alert=True)
        return
    
    chat_id = query.message.chat_id
    
    if selected_answer == correct_answer:
        # Correct answer - remove restrictions
        try:
            chat = await context.bot.get_chat(chat_id)
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=chat.permissions
            )
            
            await query.edit_message_text(
                f"✅ Captcha solved! Welcome to the chat, {query.from_user.first_name}!"
            )
            
            # Remove from pending users
            session = db.get_session()
            try:
                pending = session.query(PendingUsers).filter(
                    PendingUsers.chat_id == chat_id,
                    PendingUsers.user_id == user_id
                ).first()
                
                if pending:
                    session.delete(pending)
                    session.commit()
                
                # Send welcome message now
                settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
                if settings and settings.welcome_enabled and settings.welcome_message:
                    welcome_text = format_welcome_message(settings.welcome_message, query.from_user, query.message.chat)
                    await context.bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
            
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error handling correct captcha: {e}")
    
    else:
        # Wrong answer - kick user
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            
            await query.edit_message_text(
                f"❌ Wrong answer! {query.from_user.first_name} has been kicked."
            )
            
            # Remove from pending users
            session = db.get_session()
            try:
                pending = session.query(PendingUsers).filter(
                    PendingUsers.chat_id == chat_id,
                    PendingUsers.user_id == user_id
                ).first()
                
                if pending:
                    session.delete(pending)
                    session.commit()
            
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error handling wrong captcha: {e}")


async def handle_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Delete ALL service/system messages (pinned notifications, group-name changes,
    photo changes, group-created messages, etc.) when 'delete_all_system_msg' or
    the legacy 'delete_service' toggle is on. This mirrors @joinhider_bot's
    delete_all_system_msg option.

    Note: join/leave service messages are handled separately by
    handle_new_member_welcome / handle_left_member_goodbye with their own granular
    toggles. This handler catches the remaining service-message types.
    """
    if not update.message:
        return

    chat_id = update.effective_chat.id

    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        if not settings:
            return
        if not (settings.delete_all_system_msg or settings.delete_service):
            return
        try:
            await context.bot.delete_message(chat_id, update.message.message_id)
        except Exception as e:
            logger.error(f"Failed to delete service message in {chat_id}: {e}")
    finally:
        session.close()


# Initialize database
update_welcome_database()