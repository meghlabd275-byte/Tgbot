from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import is_admin_command, is_group_command
import logging

logger = logging.getLogger(__name__)

# Add new table for notes system
from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base

class Note(Base):
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger)
    name = Column(String(255))
    content = Column(Text)
    file_id = Column(String(255))  # For media notes
    file_type = Column(String(50))  # photo, video, document, etc.
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Rule(Base):
    __tablename__ = 'rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True)
    content = Column(Text)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

def update_notes_database():
    from database import db as database_instance
    Base.metadata.create_all(bind=database_instance.engine)

@is_admin_command
@is_group_command
async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a note"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/save <notename> <content>`\n"
            "You can also reply to a message with `/save <notename>` to save that message as a note.",
            parse_mode='Markdown'
        )
        return
    
    note_name = context.args[0].lower()
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    # Check if replying to a message
    if update.message.reply_to_message:
        replied_msg = update.message.reply_to_message
        
        # Handle different message types
        content = None
        file_id = None
        file_type = None
        
        if replied_msg.text:
            content = replied_msg.text
        elif replied_msg.caption:
            content = replied_msg.caption
        
        if replied_msg.photo:
            file_id = replied_msg.photo[-1].file_id
            file_type = 'photo'
        elif replied_msg.video:
            file_id = replied_msg.video.file_id
            file_type = 'video'
        elif replied_msg.document:
            file_id = replied_msg.document.file_id
            file_type = 'document'
        elif replied_msg.sticker:
            file_id = replied_msg.sticker.file_id
            file_type = 'sticker'
        elif replied_msg.voice:
            file_id = replied_msg.voice.file_id
            file_type = 'voice'
        elif replied_msg.video_note:
            file_id = replied_msg.video_note.file_id
            file_type = 'video_note'
        elif replied_msg.animation:
            file_id = replied_msg.animation.file_id
            file_type = 'animation'
    else:
        # Save text content
        content = ' '.join(context.args[1:])
        file_id = None
        file_type = None
    
    if not content and not file_id:
        await update.message.reply_text("❌ No content to save!")
        return
    
    session = db.get_session()
    try:
        # Check if note already exists
        existing_note = session.query(Note).filter(
            Note.chat_id == chat_id,
            Note.name == note_name
        ).first()
        
        if existing_note:
            # Update existing note
            existing_note.content = content
            existing_note.file_id = file_id
            existing_note.file_type = file_type
            existing_note.created_by = admin_id
            session.commit()
            await update.message.reply_text(f"✅ Updated note '{note_name}'")
        else:
            # Create new note
            note = Note(
                chat_id=chat_id,
                name=note_name,
                content=content,
                file_id=file_id,
                file_type=file_type,
                created_by=admin_id
            )
            session.add(note)
            session.commit()
            await update.message.reply_text(f"✅ Saved note '{note_name}'")
    
    finally:
        session.close()

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a note"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/get <notename>`")
        return
    
    note_name = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        note = session.query(Note).filter(
            Note.chat_id == chat_id,
            Note.name == note_name
        ).first()
        
        if not note:
            await update.message.reply_text(f"❌ Note '{note_name}' not found.")
            return
        
        # Send the note
        if note.file_id and note.file_type:
            # Send media note
            if note.file_type == 'photo':
                await context.bot.send_photo(
                    chat_id,
                    note.file_id,
                    caption=note.content,
                    parse_mode='Markdown'
                )
            elif note.file_type == 'video':
                await context.bot.send_video(
                    chat_id,
                    note.file_id,
                    caption=note.content,
                    parse_mode='Markdown'
                )
            elif note.file_type == 'document':
                await context.bot.send_document(
                    chat_id,
                    note.file_id,
                    caption=note.content,
                    parse_mode='Markdown'
                )
            elif note.file_type == 'sticker':
                await context.bot.send_sticker(chat_id, note.file_id)
                if note.content:
                    await context.bot.send_message(chat_id, note.content, parse_mode='Markdown')
            elif note.file_type == 'voice':
                await context.bot.send_voice(
                    chat_id,
                    note.file_id,
                    caption=note.content,
                    parse_mode='Markdown'
                )
            elif note.file_type == 'video_note':
                await context.bot.send_video_note(chat_id, note.file_id)
                if note.content:
                    await context.bot.send_message(chat_id, note.content, parse_mode='Markdown')
            elif note.file_type == 'animation':
                await context.bot.send_animation(
                    chat_id,
                    note.file_id,
                    caption=note.content,
                    parse_mode='Markdown'
                )
        else:
            # Send text note
            await context.bot.send_message(chat_id, note.content, parse_mode='Markdown')
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a note"""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/clear <notename>`")
        return
    
    note_name = context.args[0].lower()
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        note = session.query(Note).filter(
            Note.chat_id == chat_id,
            Note.name == note_name
        ).first()
        
        if note:
            session.delete(note)
            session.commit()
            await update.message.reply_text(f"✅ Deleted note '{note_name}'")
        else:
            await update.message.reply_text(f"❌ Note '{note_name}' not found.")
    
    finally:
        session.close()

async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notes"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        notes = session.query(Note).filter(Note.chat_id == chat_id).order_by(Note.name).all()
        
        if not notes:
            await update.message.reply_text("📝 No notes saved in this chat.")
            return
        
        notes_list = "📝 **Saved Notes:**\n\n"
        for note in notes:
            note_type = f" ({note.file_type})" if note.file_type else ""
            notes_list += f"• `{note.name}`{note_type}\n"
        
        notes_list += f"\n**Total:** {len(notes)} notes\n"
        notes_list += "Use `/get <notename>` to retrieve a note."
        
        await update.message.reply_text(notes_list, parse_mode='Markdown')
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def setrules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set chat rules"""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/setrules <rules text>`\n"
            "You can also reply to a message with `/setrules` to set that message as rules.",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if update.message.reply_to_message and update.message.reply_to_message.text:
        rules_text = update.message.reply_to_message.text
    else:
        rules_text = ' '.join(context.args)
    
    session = db.get_session()
    try:
        existing_rules = session.query(Rule).filter(Rule.chat_id == chat_id).first()
        
        if existing_rules:
            existing_rules.content = rules_text
            existing_rules.created_by = admin_id
            session.commit()
            await update.message.reply_text("✅ Updated chat rules!")
        else:
            rules = Rule(
                chat_id=chat_id,
                content=rules_text,
                created_by=admin_id
            )
            session.add(rules)
            session.commit()
            await update.message.reply_text("✅ Set chat rules!")
    
    finally:
        session.close()

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chat rules"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        rules = session.query(Rule).filter(Rule.chat_id == chat_id).first()
        
        if not rules:
            await update.message.reply_text("📋 No rules set for this chat.")
            return
        
        rules_text = f"📋 **{update.effective_chat.title} Rules:**\n\n{rules.content}"
        await update.message.reply_text(rules_text, parse_mode='Markdown')
    
    finally:
        session.close()

@is_admin_command
@is_group_command
async def clearrules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear chat rules"""
    chat_id = update.effective_chat.id
    
    session = db.get_session()
    try:
        rules = session.query(Rule).filter(Rule.chat_id == chat_id).first()
        
        if rules:
            session.delete(rules)
            session.commit()
            await update.message.reply_text("✅ Cleared chat rules!")
        else:
            await update.message.reply_text("❌ No rules to clear.")
    
    finally:
        session.close()

# Handle note shortcuts (e.g., #notename)
async def handle_note_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle note shortcuts like #notename"""
    if not update.message or not update.message.text:
        return False
    
    text = update.message.text.strip()
    
    # Check if message starts with # and is a single word
    if text.startswith('#') and len(text.split()) == 1:
        note_name = text[1:].lower()
        chat_id = update.effective_chat.id
        
        session = db.get_session()
        try:
            note = session.query(Note).filter(
                Note.chat_id == chat_id,
                Note.name == note_name
            ).first()
            
            if note:
                # Send the note
                if note.file_id and note.file_type:
                    if note.file_type == 'photo':
                        await context.bot.send_photo(
                            chat_id,
                            note.file_id,
                            caption=note.content,
                            parse_mode='Markdown'
                        )
                    elif note.file_type == 'video':
                        await context.bot.send_video(
                            chat_id,
                            note.file_id,
                            caption=note.content,
                            parse_mode='Markdown'
                        )
                    elif note.file_type == 'document':
                        await context.bot.send_document(
                            chat_id,
                            note.file_id,
                            caption=note.content,
                            parse_mode='Markdown'
                        )
                    elif note.file_type == 'sticker':
                        await context.bot.send_sticker(chat_id, note.file_id)
                        if note.content:
                            await context.bot.send_message(chat_id, note.content, parse_mode='Markdown')
                    # Add other media types as needed
                else:
                    await context.bot.send_message(chat_id, note.content, parse_mode='Markdown')
                
                return True
        
        finally:
            session.close()
    
    return False

# Initialize database
update_notes_database()