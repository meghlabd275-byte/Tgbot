from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command, format_user_mention
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Add new table for reports
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base

class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    reporter_id = Column(BigInteger)
    reported_user_id = Column(BigInteger)
    message_id = Column(Integer)
    reason = Column(Text)
    status = Column(String(50), default='pending')  # pending, resolved, dismissed
    handled_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime)

class ReportSettings(Base):
    __tablename__ = 'report_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    reports_enabled = Column(Boolean, default=True)
    admin_only = Column(Boolean, default=False)  # Only admins can see reports
    auto_delete_reports = Column(Boolean, default=True)
    report_cooldown = Column(Integer, default=300)  # 5 minutes
    created_at = Column(DateTime, default=func.now())

def update_reports_database():
    from database import db as database_instance
    Base.metadata.create_all(bind=database_instance.engine)

# Track report cooldowns
report_cooldowns = {}

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Report a message or user"""
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Please reply to a message to report it.\n"
            "Usage: `/report [reason]`",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    reporter_id = update.effective_user.id
    reported_message = update.message.reply_to_message
    reported_user = reported_message.from_user
    
    if not reported_user:
        await update.message.reply_text("❌ Cannot report this message.")
        return
    
    # Check if reports are enabled
    session = db.get_session()
    try:
        settings = session.query(ReportSettings).filter(ReportSettings.chat_id == chat_id).first()
        if settings and not settings.reports_enabled:
            await update.message.reply_text("❌ Reports are disabled in this chat.")
            return
        
        # Check cooldown
        cooldown_key = f"{chat_id}:{reporter_id}"
        now = datetime.now()
        
        if cooldown_key in report_cooldowns:
            time_diff = (now - report_cooldowns[cooldown_key]).total_seconds()
            cooldown_time = settings.report_cooldown if settings else 300
            
            if time_diff < cooldown_time:
                remaining = int(cooldown_time - time_diff)
                await update.message.reply_text(
                    f"⏰ Please wait {remaining} seconds before reporting again."
                )
                return
        
        # Check if user is trying to report an admin
        if db.is_admin(reported_user.id, chat_id):
            await update.message.reply_text("❌ You cannot report an admin.")
            return
        
        # Check if user is trying to report themselves
        if reporter_id == reported_user.id:
            await update.message.reply_text("❌ You cannot report yourself.")
            return
        
        # Get reason
        reason = ' '.join(context.args) if context.args else "No reason provided"
        
        # Create report
        report = Report(
            chat_id=chat_id,
            reporter_id=reporter_id,
            reported_user_id=reported_user.id,
            message_id=reported_message.message_id,
            reason=reason
        )
        session.add(report)
        session.commit()
        
        # Update cooldown
        report_cooldowns[cooldown_key] = now
        
        # Delete the report command message
        try:
            await context.bot.delete_message(chat_id, update.message.message_id)
        except:
            pass
        
        # Send report to admins
        await send_report_to_admins(context, report, reported_message, update.effective_chat)
        
        # Send confirmation to reporter
        try:
            await context.bot.send_message(
                reporter_id,
                f"✅ Your report has been sent to the admins of {update.effective_chat.title}.\n"
                f"**Reported user:** {format_user_mention(reported_user)}\n"
                f"**Reason:** {reason}",
                parse_mode='Markdown'
            )
        except:
            pass  # User might have blocked the bot
    
    finally:
        session.close()

async def send_report_to_admins(context: ContextTypes.DEFAULT_TYPE, report: Report, reported_message, chat):
    """Send report notification to admins"""
    session = db.get_session()
    try:
        # Get all admins
        admins = session.query(db.Admin).filter(db.Admin.chat_id == report.chat_id).all()
        
        # Get user info
        reporter = await context.bot.get_chat_member(report.chat_id, report.reporter_id)
        reported_user = await context.bot.get_chat_member(report.chat_id, report.reported_user_id)
        
        report_text = f"""🚨 **New Report in {chat.title}**

**Reporter:** {format_user_mention(reporter.user)}
**Reported User:** {format_user_mention(reported_user.user)}
**Reason:** {report.reason}
**Time:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}

**Reported Message:**
{reported_message.text or '[Media/Sticker/Other]'}"""
        
        # Create action buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔨 Ban", callback_data=f"report_ban_{report.id}"),
                InlineKeyboardButton("👢 Kick", callback_data=f"report_kick_{report.id}"),
                InlineKeyboardButton("🔇 Mute", callback_data=f"report_mute_{report.id}")
            ],
            [
                InlineKeyboardButton("⚠️ Warn", callback_data=f"report_warn_{report.id}"),
                InlineKeyboardButton("🗑️ Delete Msg", callback_data=f"report_delete_{report.id}")
            ],
            [
                InlineKeyboardButton("✅ Resolve", callback_data=f"report_resolve_{report.id}"),
                InlineKeyboardButton("❌ Dismiss", callback_data=f"report_dismiss_{report.id}")
            ]
        ])
        
        # Send to chat (visible to all admins)
        try:
            await context.bot.send_message(
                report.chat_id,
                report_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending report to chat: {e}")
        
        # Also send to individual admins in private
        for admin in admins:
            try:
                await context.bot.send_message(
                    admin.user_id,
                    report_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                pass  # Admin might have blocked the bot
    
    finally:
        session.close()

async def handle_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report action buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if len(data) < 3 or data[0] != 'report':
        return
    
    action = data[1]
    report_id = int(data[2])
    admin_id = query.from_user.id
    
    session = db.get_session()
    try:
        report = session.query(Report).filter(Report.id == report_id).first()
        if not report:
            await query.edit_message_text("❌ Report not found.")
            return
        
        # Check if user is admin
        if not db.is_admin(admin_id, report.chat_id):
            await query.answer("❌ You need to be an admin to handle reports!", show_alert=True)
            return
        
        # Check if report is already handled
        if report.status != 'pending':
            await query.answer("❌ This report has already been handled!", show_alert=True)
            return
        
        chat_id = report.chat_id
        reported_user_id = report.reported_user_id
        
        try:
            if action == 'ban':
                await context.bot.ban_chat_member(chat_id, reported_user_id)
                db.add_ban(reported_user_id, chat_id, admin_id, f"Report: {report.reason}")
                action_text = "banned"
                
            elif action == 'kick':
                await context.bot.ban_chat_member(chat_id, reported_user_id)
                await context.bot.unban_chat_member(chat_id, reported_user_id)
                action_text = "kicked"
                
            elif action == 'mute':
                from datetime import datetime, timedelta
                until_date = datetime.now() + timedelta(hours=1)
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=reported_user_id,
                    permissions=context.bot.get_chat(chat_id).permissions,
                    until_date=until_date
                )
                db.add_mute(reported_user_id, chat_id, admin_id, 3600, f"Report: {report.reason}")
                action_text = "muted for 1 hour"
                
            elif action == 'warn':
                db.add_warning(reported_user_id, chat_id, admin_id, f"Report: {report.reason}")
                action_text = "warned"
                
            elif action == 'delete':
                try:
                    await context.bot.delete_message(chat_id, report.message_id)
                    action_text = "message deleted"
                except:
                    action_text = "message deletion failed"
                    
            elif action == 'resolve':
                action_text = "resolved without action"
                
            elif action == 'dismiss':
                action_text = "dismissed"
            
            # Update report status
            report.status = 'resolved' if action in ['ban', 'kick', 'mute', 'warn', 'delete', 'resolve'] else 'dismissed'
            report.handled_by = admin_id
            report.resolved_at = datetime.now()
            session.commit()
            
            # Update message
            await query.edit_message_text(
                f"{query.message.text}\n\n✅ **Report {action_text} by {query.from_user.first_name}**",
                parse_mode='Markdown'
            )
            
            # Notify reporter
            try:
                await context.bot.send_message(
                    report.reporter_id,
                    f"✅ Your report has been handled.\n"
                    f"**Action taken:** {action_text.title()}\n"
                    f"**Handled by:** {query.from_user.first_name}",
                    parse_mode='Markdown'
                )
            except:
                pass
            
        except Exception as e:
            await query.edit_message_text(
                f"{query.message.text}\n\n❌ **Failed to {action}: {str(e)}**",
                parse_mode='Markdown'
            )
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle reports or show settings"""
    if not context.args:
        # Show current settings
        chat_id = update.effective_chat.id
        session = db.get_session()
        try:
            settings = session.query(ReportSettings).filter(ReportSettings.chat_id == chat_id).first()
            
            if not settings:
                settings = ReportSettings(chat_id=chat_id)
                session.add(settings)
                session.commit()
            
            # Get report statistics
            total_reports = session.query(Report).filter(Report.chat_id == chat_id).count()
            pending_reports = session.query(Report).filter(
                Report.chat_id == chat_id,
                Report.status == 'pending'
            ).count()
            
            settings_text = f"""📊 **Report Settings**

**Status:** {'✅ Enabled' if settings.reports_enabled else '❌ Disabled'}
**Admin Only:** {'✅ Yes' if settings.admin_only else '❌ No'}
**Auto Delete:** {'✅ Yes' if settings.auto_delete_reports else '❌ No'}
**Cooldown:** {settings.report_cooldown} seconds

**Statistics:**
• Total Reports: {total_reports}
• Pending Reports: {pending_reports}

**Commands:**
• `/reports on|off` - Toggle reports
• `/reports adminonly on|off` - Admin only visibility
• `/reports autodelete on|off` - Auto delete report commands
• `/reports cooldown <seconds>` - Set report cooldown
• `/reporthistory` - View report history"""
            
            await update.message.reply_text(settings_text, parse_mode='Markdown')
        
        finally:
            session.close()
        return
    
    # Handle settings
    if context.args[0].lower() in ['on', 'off']:
        status = context.args[0].lower() == 'on'
        chat_id = update.effective_chat.id
        
        session = db.get_session()
        try:
            settings = session.query(ReportSettings).filter(ReportSettings.chat_id == chat_id).first()
            
            if settings:
                settings.reports_enabled = status
                session.commit()
            else:
                settings = ReportSettings(chat_id=chat_id, reports_enabled=status)
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(f"✅ Reports {'enabled' if status else 'disabled'}.")
        
        finally:
            session.close()
    
    elif len(context.args) >= 2 and context.args[0].lower() == 'adminonly':
        status = context.args[1].lower() == 'on'
        chat_id = update.effective_chat.id
        
        session = db.get_session()
        try:
            settings = session.query(ReportSettings).filter(ReportSettings.chat_id == chat_id).first()
            
            if settings:
                settings.admin_only = status
                session.commit()
            else:
                settings = ReportSettings(chat_id=chat_id, admin_only=status)
                session.add(settings)
                session.commit()
            
            await update.message.reply_text(
                f"✅ Admin only reports {'enabled' if status else 'disabled'}."
            )
        
        finally:
            session.close()
    
    elif len(context.args) >= 2 and context.args[0].lower() == 'cooldown':
        try:
            cooldown = int(context.args[1])
            if cooldown < 0 or cooldown > 3600:
                await update.message.reply_text("❌ Cooldown must be between 0 and 3600 seconds.")
                return
            
            chat_id = update.effective_chat.id
            session = db.get_session()
            try:
                settings = session.query(ReportSettings).filter(ReportSettings.chat_id == chat_id).first()
                
                if settings:
                    settings.report_cooldown = cooldown
                    session.commit()
                else:
                    settings = ReportSettings(chat_id=chat_id, report_cooldown=cooldown)
                    session.add(settings)
                    session.commit()
                
                await update.message.reply_text(f"✅ Report cooldown set to {cooldown} seconds.")
            
            finally:
                session.close()
        
        except ValueError:
            await update.message.reply_text("❌ Invalid cooldown value.")

@is_admin_command
@is_group_command
async def reporthistory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show report history"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        reports = session.query(Report).filter(
            Report.chat_id == chat_id
        ).order_by(Report.created_at.desc()).limit(10).all()
        
        if not reports:
            await update.message.reply_text("📊 No reports found for this chat.")
            return
        
        history_text = "📊 **Recent Reports:**\n\n"
        
        for report in reports:
            status_emoji = {
                'pending': '⏳',
                'resolved': '✅',
                'dismissed': '❌'
            }.get(report.status, '❓')
            
            history_text += f"{status_emoji} **Report #{report.id}**\n"
            history_text += f"• Reporter: `{report.reporter_id}`\n"
            history_text += f"• Reported: `{report.reported_user_id}`\n"
            history_text += f"• Reason: {report.reason}\n"
            history_text += f"• Date: {report.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            if report.handled_by:
                history_text += f"• Handled by: `{report.handled_by}`\n"
            history_text += "\n"
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
    
    finally:
        session.close()

# Initialize database
update_reports_database()