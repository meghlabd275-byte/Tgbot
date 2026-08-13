"""Tests for the new URL Remover, Join Hider, and edited-message filter features."""
import os
import types
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

os.environ.setdefault('BOT_TOKEN', '1:x')
os.environ.setdefault('BOT_USERNAME', 'x')
os.environ.setdefault('SUPER_ADMIN_ID', '1')

# Ensure clean DB
for p in ('bot.db',):
    if os.path.exists(p):
        os.remove(p)


def make_update(text=None, caption=None, user_id=200, chat_id=-100, edited=False):
    """Build a fake Update-like object for filter testing."""
    msg = MagicMock()
    msg.text = text
    msg.caption = caption
    msg.message_id = 42
    msg.photo = None
    msg.video = None
    msg.document = None
    msg.sticker = None
    msg.voice = None
    msg.video_note = None
    msg.animation = None
    msg.contact = None
    msg.location = None
    msg.poll = None
    msg.forward_from = None
    msg.forward_from_chat = None
    msg.reply_to_message = None

    user = MagicMock()
    user.id = user_id
    user.first_name = 'Tester'
    user.is_bot = False

    chat = MagicMock()
    chat.id = chat_id
    chat.type = 'supergroup'

    update = MagicMock()
    update.message = None if edited else msg
    update.edited_message = msg if edited else None
    update.effective_message = msg
    update.effective_user = user
    update.effective_chat = chat
    return update


class TestURLRemover(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # DatabaseManager auto-initializes tables on import
        self.chat_id = -100

    def _set_settings(self, **kwargs):
        from database import db
        from handlers.url_remover import URLRemoverSettings
        session = db.get_session()
        try:
            s = session.query(URLRemoverSettings).filter(
                URLRemoverSettings.chat_id == self.chat_id
            ).first()
            if not s:
                s = URLRemoverSettings(chat_id=self.chat_id)
                session.add(s)
            for k, v in kwargs.items():
                setattr(s, k, v)
            session.commit()
        finally:
            session.close()

    async def test_contains_url_detection(self):
        from handlers.url_remover import contains_url, contains_invite_link
        self.assertTrue(contains_url('see https://example.com/path'))
        self.assertTrue(contains_url('visit www.google.com'))
        self.assertTrue(contains_url('check example.com/page'))
        self.assertFalse(contains_url('hello world'))
        self.assertFalse(contains_url('this.is.a.sentence'))
        self.assertTrue(contains_invite_link('join https://t.me/joinchat/abc'))
        self.assertTrue(contains_invite_link('t.me/mychannel'))
        self.assertTrue(contains_invite_link('follow @somechannel'))

    async def test_remove_urls_deletes_message(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_urls=True)
        update = make_update(text='check https://example.com')
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        ctx.bot.send_message = AsyncMock()
        ctx.bot.id = 1
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'URL remover should return True and delete the message')
        ctx.bot.delete_message.assert_called_once()

    async def test_remove_urls_skips_admins(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_urls=True)
        update = make_update(text='check https://example.com', user_id=999)
        ctx = MagicMock()
        with patch('database.db.is_admin', return_value=True), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertFalse(result, 'Admins must be exempt from URL removal')

    async def test_remove_urls_no_url_passes(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_urls=True)
        update = make_update(text='just a normal message')
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertFalse(result)
        ctx.bot.delete_message.assert_not_called()

    async def test_remove_urls_works_on_caption(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_urls=True)
        # Photo message: text is None, caption contains a URL
        update = make_update(text=None, caption='look at www.test.com')
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'URL remover should detect URLs in photo captions')
        ctx.bot.delete_message.assert_called_once()

    async def test_remove_urls_works_on_edited_message(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_urls=True)
        update = make_update(text='edited to add https://example.com', edited=True)
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'URL remover should work on edited messages')
        ctx.bot.delete_message.assert_called_once()

    async def test_invite_removal(self):
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_invites=True, remove_urls=False)
        update = make_update(text='join https://t.me/joinchat/abcdef')
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'Invite-link removal should catch t.me links')

    async def test_remove_urls_catches_hidden_text_link(self):
        """A URL hidden behind a hyperlink (text_link entity) must be caught."""
        from handlers.url_remover import check_url_remover, message_has_link
        self._set_settings(remove_urls=True)
        # Build a message whose visible text has no URL, but a text_link
        # entity points to a URL (e.g. "click here" -> https://evil.com)
        update = make_update(text='click here for info')
        msg = update.effective_message
        ent = MagicMock()
        ent.type = 'text_link'
        ent.url = 'https://evil-phishing-site.com'
        msg.entities = [ent]
        msg.caption_entities = []
        # Sanity: visible text alone should NOT trigger, but entity should
        self.assertFalse(
            __import__('handlers.url_remover', fromlist=['contains_url']).contains_url('click here for info')
        )
        self.assertTrue(message_has_link(msg), 'message_has_link must catch hidden text_link URLs')
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'URL remover must delete messages with hidden text_link URLs')
        ctx.bot.delete_message.assert_called_once()

    async def test_remove_all_links_catches_hidden_text_link(self):
        """remove_all_links mode must also catch hidden hyperlinks."""
        from handlers.url_remover import check_url_remover
        self._set_settings(remove_all_links=True, remove_urls=False, remove_invites=False)
        update = make_update(text='visit my channel')
        msg = update.effective_message
        ent = MagicMock()
        ent.type = 'text_link'
        ent.url = 'https://t.me/mychannel'
        msg.entities = [ent]
        msg.caption_entities = []
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        with patch('database.db.is_admin', return_value=False), \
             patch('database.db.is_whitelisted', return_value=False):
            result = await check_url_remover(update, ctx)
        self.assertTrue(result, 'remove-all-links must catch hidden invite links')
        ctx.bot.delete_message.assert_called_once()


class TestJoinHider(unittest.TestCase):
    def setUp(self):
        # DatabaseManager auto-initializes tables on import
        self.chat_id = -100

    def test_welcome_settings_has_granular_columns(self):
        from handlers.welcome import WelcomeSettings
        cols = {c.name for c in WelcomeSettings.__table__.columns}
        self.assertIn('delete_joined_msg', cols)
        self.assertIn('delete_left_msg', cols)
        self.assertIn('delete_service', cols)
        self.assertIn('delete_all_system_msg', cols)

    def test_joinhider_command_supports_system_option(self):
        from handlers.welcome import joinhider_command
        import inspect
        src = inspect.getsource(joinhider_command)
        self.assertIn('system', src, 'joinhider must support a system option')
        self.assertIn('delete_all_system_msg', src)

    def test_handle_service_message_exists(self):
        from handlers.welcome import handle_service_message
        self.assertTrue(callable(handle_service_message))


class TestEditedMessageHandler(unittest.IsolatedAsyncioTestCase):
    async def test_check_message_filters_handles_edited(self):
        """check_message_filters must not crash on edited messages (update.message is None)."""
        from handlers import filters as filters_mod
        update = make_update(text='https://example.com', edited=True)
        ctx = MagicMock()
        ctx.bot.delete_message = AsyncMock()
        ctx.bot.send_message = AsyncMock()
        ctx.bot.id = 1
        with patch('handlers.url_remover.check_url_remover', new=AsyncMock(return_value=True)):
            result = await filters_mod.check_message_filters(update, ctx)
        # URL remover returns True -> filters short-circuit
        self.assertTrue(result)


class TestBotRegistration(unittest.TestCase):
    def test_new_commands_importable(self):
        from handlers.url_remover import removeurls_command
        from handlers.welcome import joinhider_command
        self.assertTrue(callable(removeurls_command))
        self.assertTrue(callable(joinhider_command))

    def test_help_mentions_new_commands(self):
        from handlers.help_commands import help_command
        import inspect
        src = inspect.getsource(help_command)
        self.assertIn('/removeurls', src)
        self.assertIn('/joinhider', src)
        self.assertIn('cleanservice', src)


if __name__ == '__main__':
    unittest.main()
