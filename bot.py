#!/usr/bin/env python3
"""
Telegram Admin Bot
A comprehensive bot for managing Telegram groups with advanced moderation features.
"""

import logging
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
    pin_command, unpin_command, purge_command, del_command, spurge_command,
    adminlist_command, warnmode_command
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
    handle_message,
    handle_chat_member_update, handle_bot_added_to_chat, error_handler
)

# Import new advanced handlers
from handlers.antiflood import (
    setflood_command, setfloodmode_command, flood_command, check_flood,
    antiraid_command
)

from handlers.filters import (
    addfilter_command, removefilter_command, filters_command,
    lock_command, unlock_command, locks_command, antispam_command,
    locktypes_command, allowlist_command, unallowlist_command,
    check_message_filters
)

from handlers.welcome import (
    setwelcome_command, setgoodbye_command, welcome_command, goodbye_command,
    captcha_command, cleanservice_command, joinhider_command,
    setwelcomebutton_command, welcomebuttons_command, delwelcomebutton_command,
    welcomedelete_command,
    handle_new_member_welcome, handle_left_member_goodbye, handle_captcha_callback,
    handle_service_message
)

from handlers.quick_replies import (
    setcontract_command, delcontract_command, contracts_command,
    setkeywordlink_command, delkeywordlink_command, keywordlinks_command,
    greetingfilter_command, handle_quick_replies
)

from handlers.url_remover import (
    removeurls_command
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
    backup_command, handle_custom_command, check_night_mode,
    handle_cleanup_confirmation, check_slow_mode
)

from handlers.federations import (
    fednew_command, feddel_command, fedrename_command, fedinfo_command,
    fedadmins_command, fedpromote_command, feddemote_command,
    fedjoin_command, fedleave_command, fedchat_command,
    fedban_command, fedunban_command, fedkick_command, fedmute_command,
    fedbans_command
)

from handlers.connections import (
    connect_command, handle_connect_callback, disconnect_command,
    connection_command, reconnect_command
)

from handlers.approvals import (
    approve_command, unapprove_command, approval_command, approved_command,
    unapproveall_command, ignore_command, unignore_command, ignored_command
)

from handlers.services import (
    disable_command, resume_command, disabledgroups_command
)

from handlers.invite_links import (
    link_command, link_stat_command
)

from handlers.user_commands import (
    usercmd_command, handle_user_command
)

from handlers.stats import (
    stats_command, top_command
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
        # Owner kill-switch: when the group is disabled, the bot must not act
        # on any message (no filters, no flood checks, no notes, no custom
        # commands, no moderation). Super admin messages are the only exception
        # so the owner can still run /resume from inside the disabled group.
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id is not None and db.is_chat_disabled(chat_id):
            user_id = update.effective_user.id if update.effective_user else None
            if user_id not in Config.super_admin_ids():
                return

        # For edited messages, only run the filter pipeline (URL remover, word/
        # URL / spam / media filters) so users can't bypass them by editing a
        # message after it passes initial checks. Skip the rest of the pipeline.
        is_edited = update.edited_message is not None

        # Check night mode first
        if await check_night_mode(update, context):
            return

        # Check flood protection
        if await check_flood(update, context):
            return

        # Enforce slow mode (deletes too-fast messages, admins/whitelist exempt)
        if await check_slow_mode(update, context):
            return

        # Ignored users: the bot takes no automated action against them.
        from handlers.approvals import is_ignored
        if update.effective_user and is_ignored(update.effective_user.id, chat_id):
            return

        # Check message filters (word filters, URL filters, media filters, spam)
        if await check_message_filters(update, context):
            return

        if is_edited:
            # Nothing further to do for edited messages once filters pass.
            return

        # Check for note shortcuts (#notename)
        if await handle_note_shortcut(update, context):
            return

        # Quick replies: contract-address lookups, keyword links, greeting auto-delete
        if await handle_quick_replies(update, context):
            return

        # Check for admin-configured user commands (!name)
        if await handle_user_command(update, context):
            return

        # Check for custom commands
        if await handle_custom_command(update, context):
            return

        # Handle cleanup CONFIRM reply (staged by /cleanup)
        await handle_cleanup_confirmation(update, context)

        # Regular message handling
        await handle_message(update, context)

    except Exception as e:
        logger.error(f"Error in handle_all_messages: {e}")
        await error_handler(update, context)

def _register_handlers(application):
    """Register every command and event handler on the given application.

    Used by the main bot and by every live clone so all bots share the
    exact same feature pipeline.
    """

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
    application.add_handler(CommandHandler("spurge", spurge_command))
    application.add_handler(CommandHandler("del", del_command))
    application.add_handler(CommandHandler("delete", del_command))
    application.add_handler(CommandHandler("adminlist", adminlist_command))
    application.add_handler(CommandHandler("admins", adminlist_command))
    application.add_handler(CommandHandler("warnmode", warnmode_command))

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
    application.add_handler(CommandHandler("antiraid", antiraid_command))

    # Filter commands
    application.add_handler(CommandHandler("addfilter", addfilter_command))
    application.add_handler(CommandHandler("removefilter", removefilter_command))
    application.add_handler(CommandHandler("filters", filters_command))
    application.add_handler(CommandHandler("lock", lock_command))
    application.add_handler(CommandHandler("unlock", unlock_command))
    application.add_handler(CommandHandler("locks", locks_command))
    application.add_handler(CommandHandler("locktypes", locktypes_command))
    application.add_handler(CommandHandler("antispam", antispam_command))
    application.add_handler(CommandHandler("allowlist", allowlist_command))
    application.add_handler(CommandHandler("unallowlist", unallowlist_command))

    # Welcome system commands
    application.add_handler(CommandHandler("setwelcome", setwelcome_command))
    application.add_handler(CommandHandler("setgoodbye", setgoodbye_command))
    application.add_handler(CommandHandler("welcome", welcome_command))
    application.add_handler(CommandHandler("goodbye", goodbye_command))
    application.add_handler(CommandHandler("captcha", captcha_command))
    application.add_handler(CommandHandler("cleanservice", cleanservice_command))
    application.add_handler(CommandHandler("joinhider", joinhider_command))
    application.add_handler(CommandHandler("setwelcomebutton", setwelcomebutton_command))
    application.add_handler(CommandHandler("welcomebuttons", welcomebuttons_command))
    application.add_handler(CommandHandler("delwelcomebutton", delwelcomebutton_command))
    application.add_handler(CommandHandler("welcomedelete", welcomedelete_command))
    application.add_handler(CommandHandler("removeurls", removeurls_command))

    # Quick reply commands (contract addresses, keyword links, greeting filter)
    application.add_handler(CommandHandler("setcontract", setcontract_command))
    application.add_handler(CommandHandler("delcontract", delcontract_command))
    application.add_handler(CommandHandler("contracts", contracts_command))
    application.add_handler(CommandHandler("setkeywordlink", setkeywordlink_command))
    application.add_handler(CommandHandler("delkeywordlink", delkeywordlink_command))
    application.add_handler(CommandHandler("keywordlinks", keywordlinks_command))
    application.add_handler(CommandHandler("greetingfilter", greetingfilter_command))

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

    # Federation commands
    application.add_handler(CommandHandler("fednew", fednew_command))
    application.add_handler(CommandHandler("newfed", fednew_command))
    application.add_handler(CommandHandler("feddel", feddel_command))
    application.add_handler(CommandHandler("delfed", feddel_command))
    application.add_handler(CommandHandler("fedrename", fedrename_command))
    application.add_handler(CommandHandler("renamefed", fedrename_command))
    application.add_handler(CommandHandler("fedinfo", fedinfo_command))
    application.add_handler(CommandHandler("fedadmins", fedadmins_command))
    application.add_handler(CommandHandler("fedpromote", fedpromote_command))
    application.add_handler(CommandHandler("fpromote", fedpromote_command))
    application.add_handler(CommandHandler("feddemote", feddemote_command))
    application.add_handler(CommandHandler("fdemote", feddemote_command))
    application.add_handler(CommandHandler("fedjoin", fedjoin_command))
    application.add_handler(CommandHandler("joinfed", fedjoin_command))
    application.add_handler(CommandHandler("fedleave", fedleave_command))
    application.add_handler(CommandHandler("leavefed", fedleave_command))
    application.add_handler(CommandHandler("fedchat", fedchat_command))
    application.add_handler(CommandHandler("chatfed", fedchat_command))
    application.add_handler(CommandHandler("fban", fedban_command))
    application.add_handler(CommandHandler("fedban", fedban_command))
    application.add_handler(CommandHandler("fedunban", fedunban_command))
    application.add_handler(CommandHandler("unfban", fedunban_command))
    application.add_handler(CommandHandler("funban", fedunban_command))
    application.add_handler(CommandHandler("fedkick", fedkick_command))
    application.add_handler(CommandHandler("fkick", fedkick_command))
    application.add_handler(CommandHandler("fedmute", fedmute_command))
    application.add_handler(CommandHandler("fmute", fedmute_command))
    application.add_handler(CommandHandler("fedbans", fedbans_command))
    application.add_handler(CommandHandler("fbans", fedbans_command))

    # Connection commands
    application.add_handler(CommandHandler("connect", connect_command))
    application.add_handler(CommandHandler("disconnect", disconnect_command))
    application.add_handler(CommandHandler("connection", connection_command))
    application.add_handler(CommandHandler("connections", connection_command))
    application.add_handler(CommandHandler("reconnect", reconnect_command))

    # Approval & ignore commands
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("unapprove", unapprove_command))
    application.add_handler(CommandHandler("approval", approval_command))
    application.add_handler(CommandHandler("approved", approved_command))
    application.add_handler(CommandHandler("unapproveall", unapproveall_command))
    application.add_handler(CommandHandler("ignore", ignore_command))
    application.add_handler(CommandHandler("unignore", unignore_command))
    application.add_handler(CommandHandler("ignored", ignored_command))

    # Owner-only service controls (disable / resume / list disabled groups)
    application.add_handler(CommandHandler("disable", disable_command))
    application.add_handler(CommandHandler("disableservices", disable_command))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("resumeservices", resume_command))
    application.add_handler(CommandHandler("disabledgroups", disabledgroups_command))

    # Super-admin fleet commands: /groups, /clone, /clone_bots, /bot*, /commands
    from handlers.owner import (
        groups_command, clone_bots_command, bot_command, botdel_command,
        clone_conversation_handler,
    )
    application.add_handler(CommandHandler("groups", groups_command))
    application.add_handler(clone_conversation_handler())
    application.add_handler(CommandHandler("clone_bots", clone_bots_command))
    application.add_handler(CommandHandler("clonebots", clone_bots_command))
    application.add_handler(CommandHandler("bot", bot_command))
    application.add_handler(CommandHandler("botdel", botdel_command))

    # Invite-link system (unique per-user links + join statistics)
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("link_stat", link_stat_command))
    application.add_handler(CommandHandler("linkstats", link_stat_command))

    # Admin-controlled member commands (!name)
    application.add_handler(CommandHandler("usercmd", usercmd_command))
    application.add_handler(CommandHandler("usercmds", usercmd_command))

    # Chat statistics / leaderboard
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("statistics", stats_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("leaderboard", top_command))

    # Event handlers
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member_welcome
    ))

    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_left_member_goodbye
    ))

    # Delete ALL other service messages (pinned, title change, photo change,
    # group created, etc.) when 'delete_all_system_msg' or legacy
    # 'delete_service' is on. Excludes join/leave (handled above).
    application.add_handler(MessageHandler(
        filters.StatusUpdate.ALL
        & ~filters.StatusUpdate.NEW_CHAT_MEMBERS
        & ~filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_service_message
    ))

    # Handle forwarded messages for verification (private chats only)
    application.add_handler(MessageHandler(
        filters.FORWARDED & filters.ChatType.PRIVATE,
        handle_forwarded_message
    ))

    # Custom command fallback (admin-configured via /addcmd): any "/command"
    # that did not match a registered CommandHandler above is dispatched to
    # handle_custom_command. This runs AFTER every CommandHandler so built-in
    # commands always take precedence over user-created ones.
    application.add_handler(MessageHandler(
        filters.COMMAND,
        handle_custom_command
    ))

    # Chat member updates (promotions, bans, etc.)
    application.add_handler(ChatMemberHandler(
        handle_chat_member_update,
        ChatMemberHandler.CHAT_MEMBER
    ))

    # Bot's own membership changes (added to / removed from a chat).
    # On add, register the chat and auto-sync its admins so the admin who
    # added the bot can immediately configure the group.
    application.add_handler(ChatMemberHandler(
        handle_bot_added_to_chat,
        ChatMemberHandler.MY_CHAT_MEMBER
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
    application.add_handler(CallbackQueryHandler(
        handle_connect_callback,
        pattern=r"^connect_"
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

    # Edited message handler — re-run filters (URL remover, word/url/spam/media)
    # so that users cannot bypass link/word filters by editing a message after posting.
    application.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE & ~filters.COMMAND,
        handle_all_messages
    ))

    # Kept from original main():
    application.add_error_handler(error_handler)

    logger.info("Bot handlers registered successfully")


def build_application(token: str = None, start_clones: bool = True):
    """Build a fully-configured PTB Application with every command and event handler.

    Tokens are used only to construct the application; handlers read the
    process-wide Config at call time so one codebase powers the main bot and
    every live clone (see handlers/clonebot.py).

    When ``start_clones`` is True (default for the real main bot) the clone
    supervisor is launched first so registered 'active' clone bots come online
    in threads alongside the main process.
    """
    token = token or Config.BOT_TOKEN
    if start_clones:
        try:
            from handlers.clonebot import start_clone_supervisor
            start_clone_supervisor()
        except Exception as e:
            logger.error(f"Failed to start clone supervisor: {e}")

    application = Application.builder().token(token).build()
    _register_handlers(application)
    return application


def main():
    """Main function to run the primary (deployed) bot."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")

        # build_application() brings registered clone bots online (supervisor)
        # and returns a fully-configured application for the main bot.
        application = build_application()
        logger.info("🤖 Starting main Telegram Admin Bot...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()
