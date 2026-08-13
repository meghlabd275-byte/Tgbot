from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    delete_service = Column(Boolean, default=False)  # delete service messages
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
            f"{'Join/leave messages will be automatically deleted.' if status else ''}"
        )
    
    finally:
        session.close()

async def handle_new_member_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new member with welcome message and captcha"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        settings = session.query(WelcomeSettings).filter(WelcomeSettings.chat_id == chat_id).first()
        
        if not settings:
            return
        
        # Delete service message if enabled
        if settings.delete_service:
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
        
        for new_member in update.message.new_chat_members:
            # Skip bots
            if new_member.is_bot:
                continue
            
            # Check if captcha is enabled
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
            permissions=context.bot.get_chat(chat_id).permissions._replace(
                can_send_messages=False
            )
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
        
        # Delete service message if enabled
        if settings.delete_service:
            try:
                await context.bot.delete_message(chat_id, update.message.message_id)
            except:
                pass
        
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

# Initialize database
update_welcome_database()