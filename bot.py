#!/usr/bin/env python3
"""
Telegram Admin Bot
A comprehensive bot for managing Telegram groups with advanced moderation features.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    filters, ContextTypes
)

# Import configuration and database
from config import Config
from database import db

# Import all handlers
from handlers.admin_commands import (
    fileid_command, activate_command, silence_command, unsilence_command,
    underattack_command, ua_command, reload_command, debug_command,
    pin_command, unpin_command, purge_command
)

from handlers.user_management import (
    promote_command, title_command, demote_command,
    ban_command, sban_command, gban_command, sgban_command,
    unban_command, gunban_command, banlist_command,
    kick_command, skick_command, gkick_command,
    mute_command, unmute_command, smute_command
)

from handlers.warning_system import (
    warn_command, gwarn_command, swarn_command,
    unwarn_command, resetwarns_command, warnings_command
)

from handlers.whitelist_system import (
    whitelist_command, gwhitelist_command, unwhitelist_command,
    gunwhitelist_command, whitelisted_command, checkwhitelist_command
)

from handlers.user_info import (
    resetuser_command, resetrep_command, user_command,
    lastactive_command, id_command, chatinfo_command
)

from handlers.verification import (
    verify_command, handle_forwarded_message
)

from handlers.help_commands import (
    help_command, start_command, about_command, commands_command
)

from handlers.events import (
    handle_new_member, handle_left_member, handle_message,
    handle_chat_member_update, handle_bot_added_to_chat, error_handler
)

# Import new advanced handlers
from handlers.antiflood import (
    setflood_command, setfloodmode_command, flood_command, check_flood
)

from handlers.filters import (
    addfilter_command, removefilter_command, filters_command,
    lock_command, unlock_command, locks_command, antispam_command,
    check_message_filters
)

from handlers.welcome import (
    setwelcome_command, setgoodbye_command, welcome_command, goodbye_command,
    captcha_command, cleanservice_command, handle_new_member_welcome,
    handle_left_member_goodbye, handle_captcha_callback
)

from handlers.notes import (
    save_command, get_command, clear_command, notes_command,
    setrules_command, rules_command, clearrules_command, handle_note_shortcut
)

from handlers.reports import (
    report_command, reports_command, reporthistory_command, handle_report_callback
)

from handlers.advanced_features import (
    setlang_command, nightmode_command, slowmode_command,
    addcmd_command, delcmd_command, listcmds_command, cleanup_command,
    backup_command, handle_custom_command, check_night_mode
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Combined message handler for all filters and checks"""
    try:
        # Check night mode first
        if await check_night_mode(update, context):
            return
        
        # Check flood protection
        if await check_flood(update, context):
            return
        
        # Check message filters (word filters, URL filters, media filters, spam)
        if await check_message_filters(update, context):
            return
        
        # Check for note shortcuts (#notename)
        if await handle_note_shortcut(update, context):
            return
        
        # Check for custom commands
        if await handle_custom_command(update, context):
            return
        
        # Regular message handling
        await handle_message(update, context)
        
    except Exception as e:
        logger.error(f"Error in handle_all_messages: {e}")
        await error_handler(update, context)

async def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Create application
        application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Add command handlers
        
        # Admin utility commands
        application.add_handler(CommandHandler("fileid", fileid_command))
        
        # Chat management commands
        application.add_handler(CommandHandler("activate", activate_command))
        application.add_handler(CommandHandler("silence", silence_command))
        application.add_handler(CommandHandler("unsilence", unsilence_command))
        application.add_handler(CommandHandler("underattack", underattack_command))
        application.add_handler(CommandHandler("ua", ua_command))
        application.add_handler(CommandHandler("reload", reload_command))
        application.add_handler(CommandHandler("debug", debug_command))
        application.add_handler(CommandHandler("pin", pin_command))
        application.add_handler(CommandHandler("unpin", unpin_command))
        application.add_handler(CommandHandler("purge", purge_command))
        
        # User management commands
        application.add_handler(CommandHandler("promote", promote_command))
        application.add_handler(CommandHandler("title", title_command))
        application.add_handler(CommandHandler("demote", demote_command))
        
        application.add_handler(CommandHandler("ban", ban_command))
        application.add_handler(CommandHandler("sban", sban_command))
        application.add_handler(CommandHandler("gban", gban_command))
        application.add_handler(CommandHandler("sgban", sgban_command))
        
        application.add_handler(CommandHandler("unban", unban_command))
        application.add_handler(CommandHandler("gunban", gunban_command))
        application.add_handler(CommandHandler("banlist", banlist_command))
        
        application.add_handler(CommandHandler("kick", kick_command))
        application.add_handler(CommandHandler("skick", skick_command))
        application.add_handler(CommandHandler("gkick", gkick_command))
        
        application.add_handler(CommandHandler("mute", mute_command))
        application.add_handler(CommandHandler("unmute", unmute_command))
        application.add_handler(CommandHandler("smute", smute_command))
        
        # Warning system commands
        application.add_handler(CommandHandler("warn", warn_command))
        application.add_handler(CommandHandler("gwarn", gwarn_command))
        application.add_handler(CommandHandler("swarn", swarn_command))
        application.add_handler(CommandHandler("unwarn", unwarn_command))
        application.add_handler(CommandHandler("resetwarns", resetwarns_command))
        application.add_handler(CommandHandler("warnings", warnings_command))
        
        # Whitelist system commands
        application.add_handler(CommandHandler("whitelist", whitelist_command))
        application.add_handler(CommandHandler("gwhitelist", gwhitelist_command))
        application.add_handler(CommandHandler("unwhitelist", unwhitelist_command))
        application.add_handler(CommandHandler("gunwhitelist", gunwhitelist_command))
        application.add_handler(CommandHandler("whitelisted", whitelisted_command))
        application.add_handler(CommandHandler("checkwhitelist", checkwhitelist_command))
        
        # User info commands
        application.add_handler(CommandHandler("resetuser", resetuser_command))
        application.add_handler(CommandHandler("resetrep", resetrep_command))
        application.add_handler(CommandHandler("user", user_command))
        application.add_handler(CommandHandler("lastactive", lastactive_command))
        application.add_handler(CommandHandler("id", id_command))
        application.add_handler(CommandHandler("chatinfo", chatinfo_command))
        
        # Verification commands
        application.add_handler(CommandHandler("verify", verify_command))
        
        # Help commands
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("about", about_command))
        application.add_handler(CommandHandler("commands", commands_command))
        
        # Anti-flood commands
        application.add_handler(CommandHandler("setflood", setflood_command))
        application.add_handler(CommandHandler("setfloodmode", setfloodmode_command))
        application.add_handler(CommandHandler("flood", flood_command))
        
        # Filter commands
        application.add_handler(CommandHandler("addfilter", addfilter_command))
        application.add_handler(CommandHandler("removefilter", removefilter_command))
        application.add_handler(CommandHandler("filters", filters_command))
        application.add_handler(CommandHandler("lock", lock_command))
        application.add_handler(CommandHandler("unlock", unlock_command))
        application.add_handler(CommandHandler("locks", locks_command))
        application.add_handler(CommandHandler("antispam", antispam_command))
        
        # Welcome system commands
        application.add_handler(CommandHandler("setwelcome", setwelcome_command))
        application.add_handler(CommandHandler("setgoodbye", setgoodbye_command))
        application.add_handler(CommandHandler("welcome", welcome_command))
        application.add_handler(CommandHandler("goodbye", goodbye_command))
        application.add_handler(CommandHandler("captcha", captcha_command))
        application.add_handler(CommandHandler("cleanservice", cleanservice_command))
        
        # Notes and rules commands
        application.add_handler(CommandHandler("save", save_command))
        application.add_handler(CommandHandler("get", get_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("notes", notes_command))
        application.add_handler(CommandHandler("setrules", setrules_command))
        application.add_handler(CommandHandler("rules", rules_command))
        application.add_handler(CommandHandler("clearrules", clearrules_command))
        
        # Report system commands
        application.add_handler(CommandHandler("report", report_command))
        application.add_handler(CommandHandler("reports", reports_command))
        application.add_handler(CommandHandler("reporthistory", reporthistory_command))
        
        # Advanced feature commands
        application.add_handler(CommandHandler("setlang", setlang_command))
        application.add_handler(CommandHandler("nightmode", nightmode_command))
        application.add_handler(CommandHandler("slowmode", slowmode_command))
        application.add_handler(CommandHandler("addcmd", addcmd_command))
        application.add_handler(CommandHandler("delcmd", delcmd_command))
        application.add_handler(CommandHandler("listcmds", listcmds_command))
        application.add_handler(CommandHandler("cleanup", cleanup_command))
        application.add_handler(CommandHandler("backup", backup_command))
        
        # Event handlers
        application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS, 
            handle_new_member_welcome
        ))
        
        application.add_handler(MessageHandler(
            filters.StatusUpdate.LEFT_CHAT_MEMBER, 
            handle_left_member_goodbye
        ))
        
        # Handle bot being added to chat
        application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS & filters.User(user_id=None),  # Will be set to bot's ID
            handle_bot_added_to_chat
        ))
        
        # Handle forwarded messages for verification (private chats only)
        application.add_handler(MessageHandler(
            filters.FORWARDED & filters.ChatType.PRIVATE,
            handle_forwarded_message
        ))
        
        # Chat member updates (promotions, bans, etc.)
        application.add_handler(ChatMemberHandler(
            handle_chat_member_update,
            ChatMemberHandler.CHAT_MEMBER
        ))
        
        # Callback query handlers
        from telegram.ext import CallbackQueryHandler
        application.add_handler(CallbackQueryHandler(
            handle_captcha_callback, 
            pattern=r"^captcha_"
        ))
        application.add_handler(CallbackQueryHandler(
            handle_report_callback, 
            pattern=r"^report_"
        ))
        
        # General message handler (should be last)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_all_messages
        ))
        
        # Media message handler for filters
        application.add_handler(MessageHandler(
            ~filters.COMMAND & ~filters.StatusUpdate.ALL,
            handle_all_messages
        ))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        logger.info("Bot handlers registered successfully")
        
        # Start the bot
        logger.info("🤖 Starting Telegram Admin Bot...")
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())