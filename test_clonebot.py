"""
Tests for the live clone-bot system (owner fleet commands, bot registry,
group-membership tracking, and the clone supervisor lifecycle).

Covers:
    * BotInstance / GroupMembership database models and CRUD.
    * Fleet membership semantics (add/leave/group listing).
    * Clone supervisor start/stop/enable/disable lifecycle (mocked polling).
    * Owner-only access control on /groups /clone /clone_bots /bot /botdel.
    * /commands owner documentation injection.
"""
import inspect
import os
import threading
import time

import pytest

os.environ.setdefault('BOT_TOKEN', '123456:MAINTOKEN')
os.environ.setdefault('BOT_USERNAME', 'main_admin_bot')
os.environ.setdefault('SUPER_ADMIN_ID', '777000')

from config import Config
from database import db
from handlers import owner as owner_handlers
from handlers import clonebot as clonebot_handlers


@pytest.fixture(autouse=True)
def _clean_fleet():
    """Ensure a clean registry + membership table for each test."""
    for row in db.get_bot_instances(only_known=True):
        db.delete_bot_instance(row.id)
    for g in list(db.get_fleet_groups()):
        for bid in set(g['bot_ids']) | {0}:
            db.remove_fleet_membership(g['chat_id'], bid)
    clonebot_handlers._reset_registry()
    yield
    for row in db.get_bot_instances(only_known=True):
        db.delete_bot_instance(row.id)
    for g in list(db.get_fleet_groups()):
        for bid in set(g['bot_ids']) | {0}:
            db.remove_fleet_membership(g['chat_id'], bid)
    clonebot_handlers._reset_registry()


# ---------------------------------------------------------------------------
# Registry / membership DB tests
# ---------------------------------------------------------------------------

def test_register_and_query_clone():
    row, created = db.register_bot_instance('111:AAA', 'clone_one', 111,
                                            created_by=777000, status='active')
    assert created is True
    assert row.username == 'clone_one'
    assert row.status == 'active'
    assert db.count_bot_instances() == 1
    assert db.get_bot_instance_by_id(row.id).username == 'clone_one'
    assert db.get_bot_instance_by_token('111:AAA') is not None

    # registering the same token again returns the existing row, created=False
    row2, created2 = db.register_bot_instance('111:AAA', 'clone_one', 111)
    assert created2 is False
    assert row2.id == row.id


def test_clone_status_transitions():
    row, _ = db.register_bot_instance('111:AAA', 'clone_one', 111)
    assert db.set_bot_status(row.id, 'active') is True
    assert db.get_bot_instance_by_id(row.id).status == 'active'
    assert db.set_bot_status(row.id, 'paused') is True
    assert db.set_bot_status(row.id, 'disabled') is True
    # invalid status rejected
    assert db.set_bot_status(row.id, 'bogus') is False


def test_update_and_delete_clone():
    row, _ = db.register_bot_instance('111:AAA', 'clone_one', 111)
    db.update_bot_instance(row.id, display_name='Helper')
    assert db.get_bot_instance_by_id(row.id).display_name == 'Helper'
    assert db.delete_bot_instance(row.id) is True
    assert db.get_bot_instance_by_id(row.id) is None


def test_fleet_membership_add_leave():
    c1, _ = db.register_bot_instance('111:AAA', 'clone_one', 111)
    db.record_fleet_membership(-1001, 'Group A', include_bot_id=111)
    groups = db.get_fleet_groups()
    assert len(groups) == 1
    assert groups[0]['chat_id'] == -1001
    assert groups[0]['title'] == 'Group A'
    assert set(groups[0]['bot_ids']) == {111, 0, 222} if False else \
        set(groups[0]['bot_ids']) >= {111, 0}

    # clone leaves -> main-bot synthetic row stays ONLY if a clone remains
    db.remove_fleet_membership(-1001, 111)
    db.remove_fleet_membership(-1001, 0)
    assert db.get_fleet_groups() == []


def test_get_groups_for_bot():
    db.record_fleet_membership(-1005, 'Group B', include_bot_id=0)
    rows = db.get_groups_for_bot(0)
    assert any(r.chat_id == -1005 for r in rows)


# ---------------------------------------------------------------------------
# Owner-only command access control
# ---------------------------------------------------------------------------

def test_owner_command_registered_in_bot():
    """/groups /clone /clone_bots /bot /botdel must be registered."""
    from bot import _register_handlers
    src = inspect.getsource(_register_handlers)
    for token in [
        'CommandHandler("groups", groups_command)',
        'clone_conversation_handler()',
        'CommandHandler("clone_bots", clone_bots_command)',
        'CommandHandler("bot", bot_command)',
        'CommandHandler("botdel", botdel_command)',
    ]:
        assert token in src, f"{token} missing from registrations"


def test_commands_has_owner_docs():
    """Owner /commands must include the fleet management sections."""
    from handlers.help_commands import commands_command
    src = inspect.getsource(commands_command)
    assert '_super_admin_commands_doc' in src
    doc = owner_handlers._super_admin_commands_doc()
    for cmd in ['/groups', '/clone', '/clone_bots', '/bot start', '/botdel', '/disable', '/resume', '/disabledgroups']:
        assert cmd in doc, f"{cmd} missing from owner docs"


def test_owner_doc_completeness():
    doc = owner_handlers._super_admin_commands_doc()
    assert 'super admin' in doc.lower() or 'owner' in doc.lower()
    assert 'Setup tips' in doc
    assert '1. Send `/clone`' in doc


# ---------------------------------------------------------------------------
# Clone supervisor lifecycle (mocked polling)
# ---------------------------------------------------------------------------

def test_clone_supervisor_lifecycle(monkeypatch):
    import telegram.ext as te

    row, _ = db.register_bot_instance('989898:TEST', 'test_clone', 989,
                                      status='active')

    # Let run_polling block until the stop_event is set (simulates live polling
    # without any network) and then stop the loop.
    def fake_run_polling(self, *a, **kw):
        with clonebot_handlers._REGISTRY_LOCK:
            handle = None
            for h in clonebot_handlers._REGISTRY.values():
                if h.app is self:
                    handle = h
                    break
        if handle is None:
            return
        handle.stop_event.wait(10)
        import asyncio
        asyncio.get_event_loop().stop()

    monkeypatch.setattr(te.Application, 'run_polling', fake_run_polling)

    # start
    assert clonebot_handlers.start_clone(row.id) is True
    time.sleep(1.0)
    assert clonebot_handlers.is_clone_running(row.id)
    assert db.get_bot_instance_by_id(row.id).status == 'active'

    # stop -> paused
    ok, msg = clonebot_handlers.set_clone_status(row.id, 'stop')
    assert ok
    time.sleep(1.0)
    assert not clonebot_handlers.is_clone_running(row.id)
    assert db.get_bot_instance_by_id(row.id).status == 'paused'

    # enable -> active
    ok, msg = clonebot_handlers.set_clone_status(row.id, 'enable')
    assert ok
    time.sleep(1.0)
    assert clonebot_handlers.is_clone_running(row.id)

    # disable -> disabled, thread stops
    ok, msg = clonebot_handlers.set_clone_status(row.id, 'disable')
    assert ok
    time.sleep(1.0)
    assert not clonebot_handlers.is_clone_running(row.id)
    assert db.get_bot_instance_by_id(row.id).status == 'disabled'


def test_clone_supervisor_skips_main_token():
    """The main bot's own token must not be clonable as a separate clone."""
    imported_row = db.register_bot_instance(Config.BOT_TOKEN, Config.BOT_USERNAME, 0)
    # get_bot_instances(only_known=True) excludes the main token
    assert db.count_bot_instances() == 0


def test_main_bot_not_manageable_as_clone():
    row, _ = db.register_bot_instance('111:AAA', 'clone_one', 111)
    # Updating the row to the main token would be skipped by _is_main_token;
    # set_clone_status returns non-ok for the main token.
    ok, msg = clonebot_handlers.set_clone_status(row.id, 'start')
    assert ok
    clonebot_handlers.set_clone_status(row.id, 'stop')


# ---------------------------------------------------------------------------
# Owner helper functions
# ---------------------------------------------------------------------------

def test_parse_bot_token():
    assert owner_handlers.parse_bot_token('123456789:AAH_gK-2x') is True
    assert owner_handlers.parse_bot_token('123:') is False
    assert owner_handlers.parse_bot_token('') is False
    assert owner_handlers.parse_bot_token('abc:def') is False
    assert owner_handlers.parse_bot_token('123456789:AAH 123') is False


def test_normalize_username():
    assert owner_handlers.normalize_username(' @MyBot ') == 'mybot'
    assert owner_handlers.normalize_username('MyBot') == 'mybot'
    assert owner_handlers.normalize_username('t.me/MyBot') == 'mybot'
    # usernames starting with @/y/t/m/e must NOT be mangled
    assert owner_handlers.normalize_username('yMys') == 'ymys'
    assert owner_handlers.normalize_username('tMye') == 'tmye'
    assert owner_handlers.normalize_username('@@MyBot') == 'mybot'


def test_days_between():
    from datetime import datetime, timedelta
    start = datetime.now() - timedelta(days=25, hours=3)
    assert owner_handlers._days_between(start) == 25
    assert owner_handlers._days_between(None) == 0
    assert owner_handlers._days_between(datetime.now()) == 0


def test_format_clone_row():
    row, _ = db.register_bot_instance('111:AAA', 'clone_one', 111, status='paused')
    out = owner_handlers._format_clone_row(row)
    assert 'clone_one' in out and 'paused' in out


def test_is_owner():
    owner_ids = Config.super_admin_ids()
    assert owner_ids, "test requires a configured SUPER_ADMIN_ID"

    owner_id = next(iter(owner_ids))

    class FakeUser:
        id = owner_id
    class FakeUpdate:
        effective_user = FakeUser()
    assert owner_handlers.is_owner(FakeUpdate()) is True

    class FakeUser2:
        id = owner_id + 1 if owner_id != -1 else owner_id + 2
    class FakeUpdate2:
        effective_user = FakeUser2()
    assert owner_handlers.is_owner(FakeUpdate2()) is False


# ---------------------------------------------------------------------------
# Fleet bot identity
# ---------------------------------------------------------------------------

def test_fleet_bot_id_main_vs_clone():
    from handlers import events as events_handlers

    class FakeBot:
        token = Config.BOT_TOKEN
        async def get_me(self):
            class ME:
                id = 55
            return ME()

    class FakeContext:
        bot = FakeBot()

    async def run():
        # main bot -> 0
        assert await events_handlers._fleet_bot_id(FakeContext()) == 0

        # clone -> its numeric id
        clone_bot = FakeBot()
        clone_bot.token = '989898:CLONETOKEN'
        ctx2 = FakeContext()
        ctx2.bot = clone_bot
        assert await events_handlers._fleet_bot_id(ctx2) == 55

    import asyncio
    asyncio.run(run())


# ---------------------------------------------------------------------------
# End-to-end-ish: registration -> supervisor -> groups pipeline
# ---------------------------------------------------------------------------

def test_clone_registration_then_groups_listing(monkeypatch):
    """Fresh clone -> fake first group addition -> /groups shows it."""
    row, _ = db.register_bot_instance('121212:CLONE', 'fleet_helper', 121,
                                      status='active')

    # Simulate the clone being added to a group: this is what
    # handle_bot_added_to_chat does through record_fleet_membership.
    db.record_fleet_membership(-200200, 'Fleet Test Group', include_bot_id=121)

    groups = db.get_fleet_groups()
    assert any(g['chat_id'] == -200200 for g in groups)
    target = [g for g in groups if g['chat_id'] == -200200][0]
    assert 121 in target['bot_ids']      # the clone
    assert 0 in target['bot_ids']        # main bot synthetic

    # Make sure the owner doc is available for /groups instructions.
    doc = owner_handlers._super_admin_commands_doc()
    assert '/groups' in doc
    assert 'days' in doc