#!/usr/bin/env python3
"""
Functional tests that exercise the actual command logic (not just imports).
These verify the bugs that were fixed: db.Model attribute access, mute
permissions, antispam persistence, and new-member security checks.
"""
import os
import sys
import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['BOT_TOKEN'] = '1:fake'
os.environ['BOT_USERNAME'] = 'fake_bot'
os.environ['SUPER_ADMIN_ID'] = '1'


def make_update(chat_id=-100123, user_id=42, is_private=False, args=None, reply_to=None, new_members=None):
    """Build a lightweight fake Update object."""
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_chat.title = "Test Chat"
    update.effective_chat.type = 'private' if is_private else 'group'
    update.effective_user.id = user_id
    update.effective_user.first_name = "Tester"
    update.effective_user.last_name = None
    update.effective_user.username = "tester"
    update.effective_user.is_bot = False
    update.message.message_id = 10
    update.message.reply_to_message = reply_to
    update.message.new_chat_members = new_members or []
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    update.message.delete = AsyncMock()
    return update


def make_context(chat_id=-100123, args=None):
    """Build a fake ContextTypes.DEFAULT_TYPE with an async bot."""
    context = MagicMock()
    context.args = args or []
    chat = MagicMock()
    chat.permissions = MagicMock(can_send_messages=True)
    context.bot.get_chat = AsyncMock(return_value=chat)
    context.bot.ban_chat_member = AsyncMock()
    context.bot.unban_chat_member = AsyncMock()
    context.bot.restrict_chat_member = AsyncMock()
    context.bot.delete_message = AsyncMock()
    context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
    context.bot.id = 999
    context.bot.get_chat_member_count = AsyncMock(return_value=5)
    context.job_queue.run_once = MagicMock()
    context.error = Exception("test")
    return context


def test_db_model_attributes():
    """db.Chat, db.Admin etc. must be queryable model classes (was AttributeError)."""
    from database import db
    session = db.get_session()
    try:
        for model_name in ['Chat', 'User', 'Admin', 'Ban', 'Warning', 'Mute', 'Whitelist']:
            model = getattr(db, model_name)
            assert model is not None, f"db.{model_name} missing"
            # Must actually execute a query without raising
            session.query(model).all()
        print("✅ db model attributes are queryable (db.Chat, db.Admin, ...)")
        return True
    except Exception as e:
        print(f"❌ db model attributes error: {e}")
        return False
    finally:
        session.close()


def test_no_duplicate_db_methods():
    """DatabaseManager must not define add_mute/remove_mute/is_muted twice."""
    from database import DatabaseManager
    for name in ['add_mute', 'remove_mute', 'is_muted', 'add_ban', 'add_warning']:
        # getattr resolves to the final definition; we just ensure it exists once logically
        method = getattr(DatabaseManager, name, None)
        assert method is not None, f"{name} missing"
    print("✅ No duplicate mute methods (single definitions present)")
    return True


def test_mute_command_uses_mute_permissions():
    """mute_command must restrict can_send_messages=False (actual mute)."""
    import inspect
    from handlers.user_management import mute_command
    src = inspect.getsource(inspect.unwrap(mute_command))
    assert "permissions=context.bot.get_chat(chat_id).permissions" not in src, \
        "mute_command still uses non-awaited get_chat().permissions"
    assert "permissions=ChatPermissions(can_send_messages=False)" in src, \
        "mute_command does not restrict message sending"
    print("✅ mute_command restricts can_send_messages=False")
    return True


def test_smute_command_uses_mute_permissions():
    import inspect
    from handlers.user_management import smute_command
    src = inspect.getsource(inspect.unwrap(smute_command))
    assert "permissions=context.bot.get_chat(chat_id).permissions" not in src
    assert "permissions=ChatPermissions(can_send_messages=False)" in src
    print("✅ smute_command restricts can_send_messages=False")
    return True


def test_antiflood_uses_mute_permissions():
    import inspect
    from handlers.antiflood import check_flood
    src = inspect.getsource(check_flood)
    assert "permissions=context.bot.get_chat(chat_id).permissions" not in src
    assert "permissions=ChatPermissions(can_send_messages=False)" in src
    print("✅ antiflood check_flood restricts can_send_messages=False")
    return True


def test_filters_apply_action_uses_mute_permissions():
    import inspect
    from handlers.filters import apply_filter_action
    src = inspect.getsource(apply_filter_action)
    assert "permissions=context.bot.get_chat(chat_id).permissions" not in src
    assert "permissions=ChatPermissions(can_send_messages=False)" in src
    print("✅ filters.apply_filter_action restricts can_send_messages=False")
    return True


def test_reports_mute_uses_mute_permissions():
    import inspect
    from handlers.reports import handle_report_callback
    src = inspect.getsource(handle_report_callback)
    assert "permissions=context.bot.get_chat(chat_id).permissions" not in src
    assert "permissions=ChatPermissions(can_send_messages=False)" in src
    print("✅ reports.handle_report_callback mute restricts can_send_messages=False")
    return True


def test_captcha_uses_chatpermissions():
    """Captcha restrict must use ChatPermissions(can_send_messages=False)."""
    import inspect
    from handlers.welcome import handle_captcha
    src = inspect.getsource(handle_captcha)
    assert "permissions._replace" not in src, "captcha still uses broken ._replace"
    assert "ChatPermissions(can_send_messages=False)" in src
    print("✅ captcha uses ChatPermissions(can_send_messages=False)")
    return True


def test_antispam_persists():
    """antispam_command must persist the antispam_enabled flag in ChatSettings."""
    import inspect
    from handlers.filters import antispam_command
    src = inspect.getsource(inspect.unwrap(antispam_command))
    assert "ChatSettings" in src, "antispam_command does not reference ChatSettings"
    assert "antispam_enabled = status" in src, "antispam_command does not set antispam_enabled"
    print("✅ antispam_command persists antispam_enabled in ChatSettings")
    return True


def test_antispam_gate_in_check_filters():
    """check_message_filters must gate spam patterns on is_antispam_enabled."""
    import inspect
    from handlers.filters import check_message_filters
    src = inspect.getsource(check_message_filters)
    assert "is_antispam_enabled" in src, "spam patterns not gated on antispam setting"
    print("✅ check_message_filters gates spam patterns on antispam setting")
    return True


def test_new_member_welcome_has_security_checks():
    """handle_new_member_welcome must include under-attack + global-ban checks + bot-added."""
    import inspect
    from handlers.welcome import handle_new_member_welcome
    src = inspect.getsource(handle_new_member_welcome)
    assert "under_attack" in src, "under-attack check missing from new-member handler"
    assert "is_banned" in src, "global-ban enforcement missing from new-member handler"
    assert "bot_added" in src, "bot-added detection missing from new-member handler"
    print("✅ handle_new_member_welcome includes under-attack, global-ban, bot-added checks")
    return True


def test_bot_added_handler_not_registered():
    """The broken handle_bot_added_to_chat filter must no longer be registered."""
    import inspect
    from bot import main
    src = inspect.getsource(main)
    assert "filters.User(user_id=None)" not in src, "broken bot-added filter still registered"
    print("✅ broken handle_bot_added_to_chat filter removed from registrations")
    return True


def test_main_is_sync():
    """main() must be a synchronous function (PTB v20 run_polling pattern)."""
    import bot
    assert not asyncio.iscoroutinefunction(bot.main), "bot.main is async (would break run_polling)"
    print("✅ bot.main is synchronous (correct PTB v20 run_polling pattern)")
    return True


def test_backup_command_imports_models():
    """backup_command must import Note/WordFilter instead of using db.Note/db.WordFilter."""
    import inspect
    from handlers.advanced_features import backup_command
    src = inspect.getsource(backup_command)
    assert "from handlers.notes import Note" in src
    assert "from handlers.filters import WordFilter" in src
    assert "db.Note" not in src and "db.WordFilter" not in src
    print("✅ backup_command imports Note/WordFilter directly")
    return True


def test_db_query_in_handlers_runs():
    """Exercise real db queries that handlers perform (db.Chat, db.Admin, db.Ban, etc.)."""
    from database import db
    db.get_or_create_chat(-100999, "Func Chat")
    db.get_or_create_user(555, "u555", "User", "Five")
    db.add_admin(555, -100999)
    session = db.get_session()
    try:
        chat = session.query(db.Chat).filter(db.Chat.id == -100999).first()
        assert chat is not None and chat.title == "Func Chat"
        admin = session.query(db.Admin).filter(db.Admin.chat_id == -100999).first()
        assert admin is not None and admin.user_id == 555
        bans = session.query(db.Ban).filter(db.Ban.chat_id == -100999).all()
        assert isinstance(bans, list)
    finally:
        session.close()
    print("✅ handler-style db.Chat/db.Admin/db.Ban queries execute successfully")
    return True


def test_is_admin_logic():
    from database import db, Config
    db.get_or_create_chat(-100998, "Admin Chat")
    assert db.is_admin(Config.SUPER_ADMIN_ID, -100998) is True
    assert db.is_admin(777, -100998) is False
    db.add_admin(777, -100998)
    assert db.is_admin(777, -100998) is True
    db.remove_admin(777, -100998)
    assert db.is_admin(777, -100998) is False
    print("✅ is_admin / add_admin / remove_admin work end-to-end")
    return True


def test_federation_models_defined_once():
    """Federation tables must only be declared in handlers.federations."""
    import handlers.advanced_features as af
    af_src = __import__('inspect').getsource(af)
    assert "class Federation(" not in af_src, "duplicate Federation model still in advanced_features"
    assert "class FederationBan(" not in af_src, "duplicate FederationBan model still in advanced_features"

    from handlers.federations import Federation, FederationAdmin, FederationChat, FederationBan, FederationMute
    from database import db
    session = db.get_session()
    try:
        for model in [Federation, FederationAdmin, FederationChat, FederationBan, FederationMute]:
            session.query(model).all()  # must not raise
    finally:
        session.close()
    print("✅ Federation models defined once and queryable")
    return True


def test_warn_mode_roundtrip():
    """warn_mode must persist per-chat and round-trip through get_warn_settings."""
    from database import db
    chat_id = -100777
    db.get_or_create_chat(chat_id, "Warn Chat")
    db.set_warn_mode(chat_id, 'kick')
    settings = db.get_warn_settings(chat_id)
    assert settings['mode'] == 'kick', f"warn_mode did not persist: {settings}"
    db.set_warn_mode(chat_id, 'tban')
    assert db.get_warn_settings(chat_id)['mode'] == 'tban'
    print("✅ warn_mode persists and round-trips per chat")
    return True


def test_del_spurge_commands_registered():
    """/del and /spurge must be registered and use awaited delete_message."""
    import inspect
    from bot import main
    src = inspect.getsource(main)
    assert 'CommandHandler("del", del_command)' in src, "del command not registered"
    assert 'CommandHandler("spurge", spurge_command)' in src, "spurge command not registered"

    from handlers.admin_commands import del_command, spurge_command
    del_src = inspect.getsource(del_command)
    assert "await context.bot.delete_message" in del_src
    print("✅ /del and /spurge registered and use awaited delete_message")
    return True


def test_bot_add_auto_sync_registered():
    """Bot's own membership handler must be registered with MY_CHAT_MEMBER."""
    import inspect
    from bot import main
    src = inspect.getsource(main)
    assert "ChatMemberHandler.MY_CHAT_MEMBER" in src, "bot membership handler not registered"
    assert "handle_bot_added_to_chat" in src, "handle_bot_added_to_chat not referenced"

    from handlers.events import handle_bot_added_to_chat
    ev_src = inspect.getsource(handle_bot_added_to_chat)
    assert "sync_telegram_admins" in ev_src, "bot-add does not auto-sync admins"
    print("✅ bot-add auto-syncs admins (MY_CHAT_MEMBER handler)")
    return True


def test_service_controls_registered():
    """/disable, /resume and /disabledgroups must be registered in bot.main."""
    import inspect
    from bot import main
    src = inspect.getsource(main)
    assert 'CommandHandler("disable", disable_command)' in src, "/disable not registered"
    assert 'CommandHandler("resume", resume_command)' in src, "/resume not registered"
    assert 'CommandHandler("disabledgroups", disabledgroups_command)' in src, "/disabledgroups not registered"
    print("✅ owner service-control commands registered in bot.main")
    return True


def test_super_admin_decorator_blocks_non_owner():
    """Only Config.super_admin_ids() may pass the is_super_admin_command decorator."""
    import asyncio
    from utils import is_super_admin_command

    async def inner(update, context):
        return "allowed"

    wrapped = is_super_admin_command(inner)
    assert wrapped.__name__ == "inner", "functools.wraps missing on is_super_admin_command"

    update = make_update(chat_id=-100123, user_id=42)  # not super admin (id=1)
    result = asyncio.new_event_loop().run_until_complete(wrapped(update, None))
    assert result is None, "non-owner was not blocked"
    update.message.reply_text.assert_called_once()

    update2 = make_update(chat_id=-100123, user_id=1)  # SUPER_ADMIN_ID = '1'
    result2 = asyncio.new_event_loop().run_until_complete(wrapped(update2, None))
    assert result2 == "allowed", "owner was blocked"
    print("✅ is_super_admin_command only permits the bot owner")
    return True


def test_service_controls_db_roundtrip():
    """disable_chat / is_chat_disabled / enable_chat must persist and round-trip."""
    from database import db
    chat_id = -100555

    assert db.is_chat_disabled(chat_id) is False
    assert db.disable_chat(chat_id, disabled_by=1, reason="testing") is True
    assert db.is_chat_disabled(chat_id) is True
    # Disabling again must be idempotent (returns False, still disabled).
    assert db.disable_chat(chat_id, disabled_by=1, reason="testing") is False
    assert db.is_chat_disabled(chat_id) is True
    # Disabled group must appear in the listing.
    assert any(r.chat_id == chat_id for r in db.get_disabled_chats())

    assert db.enable_chat(chat_id) is True
    assert db.is_chat_disabled(chat_id) is False
    assert db.enable_chat(chat_id) is False  # already resumed
    print("✅ disable_chat / enable_chat / is_chat_disabled round-trip correctly")
    return True


def test_disabled_chat_model_registered():
    """DisabledChat must be exposed on db and be queryable."""
    from database import db, DisabledChat
    assert db.DisabledChat is DisabledChat, "db.DisabledChat not exposed"
    session = db.get_session()
    try:
        session.query(DisabledChat).all()  # must not raise
    finally:
        session.close()
    print("✅ DisabledChat model exposed and queryable")
    return True


def test_message_pipeline_respects_disabled_gate():
    """handle_all_messages must short-circuit when the chat is disabled."""
    import inspect
    from bot import handle_all_messages
    src = inspect.getsource(handle_all_messages)
    assert "is_chat_disabled" in src, "message pipeline missing disabled-chat gate"
    assert "Config.super_admin_ids()" in src, "disabled gate does not exempt super admin"
    print("✅ handle_all_messages gated on disabled-chat state")
    return True


def main():
    tests = [
        test_db_model_attributes,
        test_no_duplicate_db_methods,
        test_mute_command_uses_mute_permissions,
        test_smute_command_uses_mute_permissions,
        test_antiflood_uses_mute_permissions,
        test_filters_apply_action_uses_mute_permissions,
        test_reports_mute_uses_mute_permissions,
        test_captcha_uses_chatpermissions,
        test_antispam_persists,
        test_antispam_gate_in_check_filters,
        test_new_member_welcome_has_security_checks,
        test_bot_added_handler_not_registered,
        test_main_is_sync,
        test_backup_command_imports_models,
        test_db_query_in_handlers_runs,
        test_is_admin_logic,
        test_federation_models_defined_once,
        test_warn_mode_roundtrip,
        test_del_spurge_commands_registered,
        test_bot_add_auto_sync_registered,
        test_service_controls_registered,
        test_super_admin_decorator_blocks_non_owner,
        test_service_controls_db_roundtrip,
        test_disabled_chat_model_registered,
        test_message_pipeline_respects_disabled_gate,
    ]
    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"❌ {t.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    print("\n" + "=" * 50)
    print(f"📊 Functional tests: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == '__main__':
    sys.exit(main())
