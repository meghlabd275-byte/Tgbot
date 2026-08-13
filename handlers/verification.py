from telegram import Update
from telegram.ext import ContextTypes
from database import db
import logging

logger = logging.getLogger(__name__)

async def verify_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verify if a forwarded message is from an admin.
    This handler is called when someone forwards a message to the bot in private.
    """
    if update.effective_chat.type != 'private':
        return  # Only work in private chats
    
    message = update.message
    if not message.forward_from:
        await message.reply_text(
            "❌ This message is not forwarded. Please forward a message from the user you want to verify."
        )
        return
    
    forwarded_user = message.forward_from
    verifier_user = update.effective_user
    
    # Check if the forwarded user is an admin in any chat where the bot is present
    session = db.get_session()
    try:
        # Get all chats where the forwarded user is an admin
        admin_chats = session.query(db.Admin).filter(
            db.Admin.user_id == forwarded_user.id
        ).all()
        
        if not admin_chats:
            await message.reply_text(
                f"❌ **Verification Result: NOT AN ADMIN**\n\n"
                f"👤 **User:** {forwarded_user.first_name} "
                f"{forwarded_user.last_name or ''} (@{forwarded_user.username or 'No username'})\n"
                f"🆔 **ID:** `{forwarded_user.id}`\n\n"
                f"This user is not registered as an admin in any chat where this bot is active.",
                parse_mode='Markdown'
            )
            return
        
        # Get chat information for admin chats
        admin_chat_info = []
        for admin in admin_chats:
            chat = session.query(db.Chat).filter(db.Chat.id == admin.chat_id).first()
            if chat:
                admin_chat_info.append({
                    'chat_title': chat.title or f"Chat {chat.id}",
                    'chat_id': chat.id,
                    'title': admin.title,
                    'added_date': admin.created_at
                })
        
        # Format verification message
        verification_msg = f"✅ **Verification Result: VERIFIED ADMIN**\n\n"
        verification_msg += f"👤 **User:** {forwarded_user.first_name} "
        verification_msg += f"{forwarded_user.last_name or ''}"
        if forwarded_user.username:
            verification_msg += f" (@{forwarded_user.username})"
        verification_msg += f"\n🆔 **ID:** `{forwarded_user.id}`\n\n"
        
        verification_msg += f"🛡️ **Admin Status Confirmed**\n"
        verification_msg += f"This user is a verified admin in {len(admin_chat_info)} chat(s):\n\n"
        
        for i, chat_info in enumerate(admin_chat_info[:5], 1):  # Limit to 5 chats
            verification_msg += f"**{i}.** {chat_info['chat_title']}\n"
            verification_msg += f"   • Chat ID: `{chat_info['chat_id']}`\n"
            if chat_info['title']:
                verification_msg += f"   • Title: {chat_info['title']}\n"
            verification_msg += f"   • Admin since: {chat_info['added_date'].strftime('%Y-%m-%d')}\n\n"
        
        if len(admin_chat_info) > 5:
            verification_msg += f"... and {len(admin_chat_info) - 5} more chat(s)\n\n"
        
        verification_msg += f"⚠️ **Security Note:** This verification confirms the user is an admin "
        verification_msg += f"in chats where this bot is present. Always verify through official channels "
        verification_msg += f"for important matters."
        
        await message.reply_text(verification_msg, parse_mode='Markdown')
        
        # Log the verification attempt
        logger.info(
            f"Admin verification: User {verifier_user.id} verified admin status of user {forwarded_user.id}"
        )
        
    finally:
        session.close()

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command to verify admin status. Can be used in groups or private.
    """
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "🔍 **Admin Verification Service**\n\n"
            "To verify if someone is an admin:\n"
            "1. Forward any message from that user to this bot\n"
            "2. I'll check if they're an admin in any chat where I'm present\n"
            "3. You'll get a detailed verification report\n\n"
            "This helps you identify legitimate admins and avoid scammers."
        )
    else:
        # In groups, show basic verification info
        await update.message.reply_text(
            "🔍 **Admin Verification**\n\n"
            "Forward any message from a user to me in private chat to verify their admin status.\n"
            "This helps prevent admin impersonation scams."
        )

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle any forwarded message in private chat for verification.
    """
    if update.effective_chat.type != 'private':
        return
    
    if update.message.forward_from:
        await verify_admin_message(update, context)
    elif update.message.forward_from_chat:
        # Handle forwarded messages from channels/groups
        await update.message.reply_text(
            "ℹ️ This message is forwarded from a channel or group. "
            "I can only verify individual users. Please forward a message from a specific user."
        )
    else:
        # Not a forwarded message, ignore
        pass