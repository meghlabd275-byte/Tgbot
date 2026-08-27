from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(255))
    is_active = Column(Boolean, default=False)
    is_silenced = Column(Boolean, default=False)
    under_attack = Column(Boolean, default=False)
    pinned_message_id = Column(Integer)
    # How warnings issued in this chat behave:
    #   kick   - kick the user when warning limit is reached
    #   ban    - ban the user when warning limit is reached (default)
    #   mute   - mute the user when warning limit is reached
    #   tban   - temporarily ban (24h) when warning limit is reached
    warn_mode = Column(String(10), default='ban')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    reputation = Column(Integer, default=0)
    last_active = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    title = Column(String(255))
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Ban(Base):
    __tablename__ = 'bans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    banned_by = Column(BigInteger)
    reason = Column(Text)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Warning(Base):
    __tablename__ = 'warnings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    warned_by = Column(BigInteger)
    reason = Column(Text)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Mute(Base):
    __tablename__ = 'mutes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    muted_by = Column(BigInteger)
    reason = Column(Text)
    until = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

class Whitelist(Base):
    __tablename__ = 'whitelist'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    added_by = Column(BigInteger)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class DisabledChat(Base):
    """Group-level kill-switch controlled exclusively by the bot owner.

    When a chat is present in this table, the bot stops servicing that group
    entirely (messages, joins/leaves, captchas, filters, moderation commands,
    federations, reports, ...). Only the bot owner (super admin) can disable or
    resume a group; group admins cannot resume a disabled group.
    """
    __tablename__ = 'disabled_chats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False, unique=True, index=True)
    disabled_by = Column(BigInteger)
    reason = Column(Text)
    scope = Column(String(16), default='all')  # reserved: 'all' (all services)
    created_at = Column(DateTime, default=func.now())


class BotInstance(Base):
    """A cloned bot instance registered by the owner via /clone.

    Every clone is *live*: it shares the main bot's full feature set and runs
    in the same process (no separate deployment is required). Only the bot
    owner (super admin) can register or manage clones.

    Status values:
        active   — application is running and polling updates (live)
        paused   — polling is stopped but the bot can be resumed quickly
        disabled — permanently stopped; must be enabled again before running
    """
    __tablename__ = 'bot_instances'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    bot_id = Column(BigInteger, unique=True)          # Telegram numeric bot id
    display_name = Column(String(255))                # optional friendly label
    status = Column(String(16), default='disabled')   # active | paused | disabled
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class GroupMembership(Base):
    """Groups that bot instances have been added to.

    One row per (bot, chat). When *any* bot in the fleet (the main bot or a
    clone) is added to a group, membership is recorded for every known bot so
    the owner's /groups command can show the complete fleet-wide picture.
    """
    __tablename__ = 'group_memberships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(BigInteger, index=True)           # 0 = the main bot
    chat_id = Column(BigInteger, index=True)
    chat_title = Column(String(255))
    joined_at = Column(DateTime, default=func.now())

    __table_args__ = (
        # A bot is either in a chat or it is not; (bot_id, chat_id) is unique.
        UniqueConstraint('bot_id', 'chat_id', name='uq_group_memberships_bot_chat'),
    )

class DatabaseManager:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or Config.DATABASE_URL

        url_lower = (self.database_url or '').lower()
        self.backend = 'sqlite'
        engine_kwargs = {}

        if url_lower.startswith('postgresql'):
            # Production Postgres: use a connection pool tuned for managed
            # databases that close idle connections after a few minutes.
            engine_kwargs.update(
                pool_pre_ping=True,     # verify connections are alive before use
                pool_timeout=30,
            )
            self.backend = 'postgresql'
            logger.info("Using PostgreSQL database backend")
        elif url_lower.startswith('mysql'):
            # MySQL/MariaDB: pool tuning for long-lived bot processes.
            engine_kwargs.update(
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_timeout=30,
            )
            self.backend = 'mysql'
            logger.info("Using MySQL database backend")
        else:
            engine_kwargs.update(
                connect_args={"check_same_thread": False},
                # SQLite opens a new file handle per process by default and
                # does not benefit from long-lived pooled connections. NullPool
                # closes each connection as soon as it is returned, which keeps
                # the bot leak-free and avoids "unclosed database" warnings at
                # interpreter shutdown.
                poolclass=NullPool,
            )
            logger.info("Using SQLite database backend")

        self.engine = create_engine(self.database_url, **engine_kwargs)
        # expire_on_commit=False keeps attribute values loaded after commit so
        # ORM rows returned by helpfully-named methods (e.g. register_bot_instance)
        # can be read even after their session is closed.
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=self.engine
        )
        self._create_all()

        # Expose model classes so handlers can do `session.query(db.Chat)` etc.
        self.Chat = Chat
        self.User = User
        self.Admin = Admin
        self.Ban = Ban
        self.Warning = Warning
        self.Mute = Mute
        self.Whitelist = Whitelist
        self.DisabledChat = DisabledChat
        self.BotInstance = BotInstance
        self.GroupMembership = GroupMembership
        self.Base = Base

    def _create_all(self):
        """Create all tables known to this module's Base."""
        Base.metadata.create_all(bind=self.engine)

    def ensure_tables(self, *bases):
        """Create tables declared on any metadata object (e.g. handler modules).

        Handler modules declare their own models on `database.Base` (same
        metadata) but we also accept extra `Base` objects for robustness with
        future refactors.
        """
        for base in bases:
            if base.metadata is not Base.metadata:
                base.metadata.create_all(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

    def ping(self):
        """Return True if the database connection is usable."""
        try:
            session = self.get_session()
            try:
                session.connection()
                return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False

    def get_or_create_chat(self, chat_id: int, title: str = None):
        session = self.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                chat = Chat(id=chat_id, title=title)
                session.add(chat)
                session.commit()
            elif title and chat.title != title:
                chat.title = title
                session.commit()
            return chat
        finally:
            session.close()
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id, username=username, first_name=first_name, last_name=last_name)
                session.add(user)
                session.commit()
            else:
                # Update user info
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.last_active = datetime.now()
                session.commit()
            return user
        finally:
            session.close()
    
    def is_admin(self, user_id: int, chat_id: int = None):
        session = self.get_session()
        try:
            if user_id in Config.super_admin_ids():
                return True

            query = session.query(Admin).filter(Admin.user_id == user_id)
            if chat_id:
                query = query.filter(Admin.chat_id == chat_id)

            return query.first() is not None
        finally:
            session.close()

    def is_chat_admin(self, user_id: int, chat_id: int) -> bool:
        """True if user is a registered admin for the specific chat (not super admin)."""
        session = self.get_session()
        try:
            return session.query(Admin).filter(
                Admin.user_id == user_id,
                Admin.chat_id == chat_id
            ).first() is not None
        finally:
            session.close()

    def get_chat_admins(self, chat_id: int):
        """Return all registered admin rows for a chat."""
        session = self.get_session()
        try:
            return session.query(Admin).filter(Admin.chat_id == chat_id).all()
        finally:
            session.close()

    def set_chat_active(self, chat_id: int, active: bool = True):
        """Mark a chat as active (or inactive).

        The `chats.is_active` flag is what powers the web dashboard's
        "Active Chats" statistic and the "Active/Inactive" badge. It is set to
        `True` when an admin runs `/activate`, so the flag reflects reality
        instead of staying `False` forever.
        """
        session = self.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.is_active = active
                session.commit()
        finally:
            session.close()
    
    def add_admin(self, user_id: int, chat_id: int, title: str = None):
        session = self.get_session()
        try:
            existing = session.query(Admin).filter(
                Admin.user_id == user_id, 
                Admin.chat_id == chat_id
            ).first()
            
            if not existing:
                admin = Admin(user_id=user_id, chat_id=chat_id, title=title)
                session.add(admin)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def remove_admin(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            admin = session.query(Admin).filter(
                Admin.user_id == user_id, 
                Admin.chat_id == chat_id
            ).first()
            
            if admin:
                session.delete(admin)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_warn_settings(self, chat_id: int) -> dict:
        """Return warning settings for a chat: (limit, mode)."""
        session = self.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return {'limit': Config.MAX_WARNINGS, 'mode': 'ban'}
            return {'limit': Config.MAX_WARNINGS, 'mode': chat.warn_mode or 'ban'}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Owner kill-switch: disable / resume all bot services per group.
    # Only the bot owner (super admin) may call these; see the super-admin
    # command decorator in utils.py.
    # ------------------------------------------------------------------

    def disable_chat(self, chat_id: int, disabled_by: int, reason: str = None) -> bool:
        """Disable ALL bot services in `chat_id`. Returns False if already disabled."""
        session = self.get_session()
        try:
            existing = session.query(DisabledChat).filter(DisabledChat.chat_id == chat_id).first()
            if existing:
                if reason and existing.reason != reason:
                    existing.reason = reason
                    session.commit()
                return False
            session.add(DisabledChat(chat_id=chat_id, disabled_by=disabled_by, reason=reason))
            session.commit()
            return True
        finally:
            session.close()

    def enable_chat(self, chat_id: int) -> bool:
        """Resume ALL bot services in `chat_id`. Returns True if it was disabled."""
        session = self.get_session()
        try:
            rows = session.query(DisabledChat).filter(DisabledChat.chat_id == chat_id).all()
            if not rows:
                return False
            for row in rows:
                session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    def is_chat_disabled(self, chat_id: int) -> bool:
        """True if the bot is disabled (kill-switched) for this chat."""
        session = self.get_session()
        try:
            return session.query(DisabledChat).filter(DisabledChat.chat_id == chat_id).first() is not None
        finally:
            session.close()

    def get_disabled_chats(self) -> list:
        """Return the list of disabled chats (each an ORM object)."""
        session = self.get_session()
        try:
            return session.query(DisabledChat).order_by(DisabledChat.created_at.desc()).all()
        finally:
            session.close()

    def disabled_chat_count(self) -> int:
        """Number of groups whose services are currently disabled."""
        session = self.get_session()
        try:
            return session.query(DisabledChat).count()
        finally:
            session.close()

    def set_warn_mode(self, chat_id: int, mode: str):
        session = self.get_session()
        try:
            chat = session.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                chat = Chat(id=chat_id, warn_mode=mode)
                session.add(chat)
            else:
                chat.warn_mode = mode
            session.commit()
        finally:
            session.close()

    def is_approved(self, user_id: int, chat_id: int) -> bool:
        """True if the user is approved (immune to automated actions) in this chat."""
        try:
            from handlers.approvals import Approved
        except Exception:
            return False
        session = self.get_session()
        try:
            return session.query(Approved).filter(
                Approved.chat_id == chat_id,
                Approved.user_id == user_id
            ).first() is not None
        finally:
            session.close()
    
    def is_banned(self, user_id: int, chat_id: int = None):
        session = self.get_session()
        try:
            query = session.query(Ban).filter(Ban.user_id == user_id)
            if chat_id:
                query = query.filter((Ban.chat_id == chat_id) | (Ban.is_global == True))
            else:
                query = query.filter(Ban.is_global == True)
            
            return query.first() is not None
        finally:
            session.close()
    
    def add_ban(self, user_id: int, chat_id: int, banned_by: int, reason: str = None, is_global: bool = False):
        session = self.get_session()
        try:
            ban = Ban(
                user_id=user_id, 
                chat_id=chat_id, 
                banned_by=banned_by, 
                reason=reason, 
                is_global=is_global
            )
            session.add(ban)
            session.commit()
        finally:
            session.close()
    
    def remove_ban(self, user_id: int, chat_id: int = None, is_global: bool = False):
        session = self.get_session()
        try:
            query = session.query(Ban).filter(Ban.user_id == user_id)
            if is_global:
                query = query.filter(Ban.is_global == True)
            elif chat_id:
                query = query.filter(Ban.chat_id == chat_id)
            
            bans = query.all()
            for ban in bans:
                session.delete(ban)
            session.commit()
            return len(bans) > 0
        finally:
            session.close()
    
    def get_warnings_count(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            return session.query(Warning).filter(
                Warning.user_id == user_id,
                (Warning.chat_id == chat_id) | (Warning.is_global == True)
            ).count()
        finally:
            session.close()
    
    def add_warning(self, user_id: int, chat_id: int, warned_by: int, reason: str = None, is_global: bool = False):
        session = self.get_session()
        try:
            warning = Warning(
                user_id=user_id,
                chat_id=chat_id,
                warned_by=warned_by,
                reason=reason,
                is_global=is_global
            )
            session.add(warning)
            session.commit()
        finally:
            session.close()
    
    def remove_warning(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            warning = session.query(Warning).filter(
                Warning.user_id == user_id,
                Warning.chat_id == chat_id
            ).order_by(Warning.created_at.desc()).first()
            
            if warning:
                session.delete(warning)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def reset_warnings(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            warnings = session.query(Warning).filter(
                Warning.user_id == user_id,
                Warning.chat_id == chat_id
            ).all()
            
            for warning in warnings:
                session.delete(warning)
            session.commit()
            return len(warnings)
        finally:
            session.close()
    
    def is_muted(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            mute = session.query(Mute).filter(
                Mute.user_id == user_id,
                Mute.chat_id == chat_id,
                Mute.until > datetime.now()
            ).first()
            
            return mute is not None
        finally:
            session.close()
    
    def add_mute(self, user_id: int, chat_id: int, muted_by: int, duration: int, reason: str = None):
        session = self.get_session()
        try:
            until = datetime.now() + timedelta(seconds=duration)
            mute = Mute(
                user_id=user_id,
                chat_id=chat_id,
                muted_by=muted_by,
                reason=reason,
                until=until
            )
            session.add(mute)
            session.commit()
        finally:
            session.close()
    
    def remove_mute(self, user_id: int, chat_id: int):
        session = self.get_session()
        try:
            mutes = session.query(Mute).filter(
                Mute.user_id == user_id,
                Mute.chat_id == chat_id
            ).all()
            
            for mute in mutes:
                session.delete(mute)
            session.commit()
            return len(mutes) > 0
        finally:
            session.close()
    
    def is_whitelisted(self, user_id: int, chat_id: int = None):
        session = self.get_session()
        try:
            query = session.query(Whitelist).filter(Whitelist.user_id == user_id)
            if chat_id:
                query = query.filter((Whitelist.chat_id == chat_id) | (Whitelist.is_global == True))
            else:
                query = query.filter(Whitelist.is_global == True)
            
            return query.first() is not None
        finally:
            session.close()
    
    def add_whitelist(self, user_id: int, chat_id: int, added_by: int, is_global: bool = False):
        session = self.get_session()
        try:
            existing = session.query(Whitelist).filter(
                Whitelist.user_id == user_id,
                Whitelist.chat_id == chat_id,
                Whitelist.is_global == is_global
            ).first()
            
            if not existing:
                whitelist = Whitelist(
                    user_id=user_id,
                    chat_id=chat_id,
                    added_by=added_by,
                    is_global=is_global
                )
                session.add(whitelist)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def remove_whitelist(self, user_id: int, chat_id: int = None, is_global: bool = False):
        session = self.get_session()
        try:
            query = session.query(Whitelist).filter(Whitelist.user_id == user_id)
            if is_global:
                query = query.filter(Whitelist.is_global == True)
            elif chat_id:
                query = query.filter(Whitelist.chat_id == chat_id)
            
            whitelists = query.all()
            for whitelist in whitelists:
                session.delete(whitelist)
            session.commit()
            return len(whitelists) > 0
        finally:
            session.close()

# ------------------------------------------------------------------
    # Clone-bot registry (BotInstance) — owner-only management.
    # ------------------------------------------------------------------

    @staticmethod
    def _is_main_token(token: str) -> bool:
        """True if ``token`` is the main bot's token from the environment."""
        return bool(token) and token == Config.BOT_TOKEN

    def get_bot_instance_by_id(self, instance_id: int):
        """Return a BotInstance row by its database id (or None)."""
        session = self.get_session()
        try:
            return session.query(BotInstance).filter(BotInstance.id == instance_id).first()
        finally:
            session.close()

    def get_bot_instances(self, only_known: bool = True):
        """Return all registered bot instances (excluding the main bot).

        When ``only_known`` is False the main bot (token equal to the env
        BOT_TOKEN) is also included as a synthetic row, which is handy for the
        /groups fleet-wide listing.
        """
        session = self.get_session()
        try:
            rows = session.query(BotInstance).order_by(BotInstance.created_at.asc()).all()
            if only_known:
                return rows
            known = {r.token for r in rows}
            main_token = Config.BOT_TOKEN
            if main_token and main_token not in known:
                synthetic = BotInstance(
                    token=main_token,
                    username=Config.BOT_USERNAME,
                    display_name='Main bot',
                    status='active',
                )
                synthetic.id = 0
                rows.insert(0, synthetic)
            return rows
        finally:
            session.close()

    def get_bot_instance_by_token(self, token: str):
        """Return a BotInstance row by bot token (or None)."""
        session = self.get_session()
        try:
            return session.query(BotInstance).filter(BotInstance.token == token).first()
        finally:
            session.close()

    def register_bot_instance(self, token: str, username: str, bot_id: int,
                              display_name: str = None, created_by: int = None,
                              status: str = 'disabled'):
        """Register a new clone bot. Returns (row, created).

        The main bot's own token is never accepted as a clone.
        """
        if self._is_main_token(token):
            return None, False
        session = self.get_session()
        try:
            existing = session.query(BotInstance).filter(
                (BotInstance.token == token) | (BotInstance.username == username) | (BotInstance.bot_id == bot_id)
            ).first()
            if existing:
                if existing.bot_id != bot_id and bot_id is not None:
                    existing.bot_id = bot_id
                    session.commit()
                return existing, False
            row = BotInstance(
                token=token,
                username=username,
                bot_id=bot_id,
                display_name=display_name,
                created_by=created_by,
                status=status,
            )
            session.add(row)
            session.commit()
            return row, True
        finally:
            session.close()

    def update_bot_instance(self, instance_id: int, **fields):
        """Update one or more fields on a BotInstance row. Returns the row."""
        allowed = {'username', 'bot_id', 'display_name', 'status'}
        session = self.get_session()
        try:
            row = session.query(BotInstance).filter(BotInstance.id == instance_id).first()
            if not row:
                return None
            for key, value in fields.items():
                if key in allowed:
                    setattr(row, key, value)
            session.commit()
            return row
        finally:
            session.close()

    def set_bot_status(self, instance_id: int, status: str) -> bool:
        """Set a clone's status to active|paused|disabled. Returns True on change."""
        if status not in ('active', 'paused', 'disabled'):
            return False
        session = self.get_session()
        try:
            row = session.query(BotInstance).filter(BotInstance.id == instance_id).first()
            if not row:
                return False
            row.status = status
            session.commit()
            return True
        finally:
            session.close()

    def delete_bot_instance(self, instance_id: int) -> bool:
        """Remove a clone bot from the registry (and its group memberships)."""
        session = self.get_session()
        try:
            row = session.query(BotInstance).filter(BotInstance.id == instance_id).first()
            if not row:
                return False
            session.query(GroupMembership).filter(GroupMembership.bot_id == row.bot_id).delete()
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    def count_bot_instances(self) -> int:
        """Number of registered clone bots."""
        session = self.get_session()
        try:
            return session.query(BotInstance).count()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Fleet-wide group membership registry (GroupMembership).
    # ------------------------------------------------------------------

    def record_group_membership(self, bot_id: int, chat_id: int, chat_title: str = None):
        """Record that ``bot_id`` is a member of ``chat_id`` (idempotent)."""
        session = self.get_session()
        try:
            row = session.query(GroupMembership).filter(
                GroupMembership.bot_id == bot_id,
                GroupMembership.chat_id == chat_id,
            ).first()
            if row:
                if chat_title and row.chat_title != chat_title:
                    row.chat_title = chat_title
                    session.commit()
                return row, False
            row = GroupMembership(bot_id=bot_id, chat_id=chat_id, chat_title=chat_title)
            session.add(row)
            session.commit()
            return row, True
        finally:
            session.close()

    def record_fleet_membership(self, chat_id: int, chat_title: str = None,
                                include_bot_id: int = None):
        """Record a chat membership for *every* bot in the fleet.

        Called when any bot (main or clone) is added to a group. ``include_bot_id``
        is the numeric id of the bot that physically joined; membership is also
        recorded for the main bot (bot_id=0) and every registered clone so the
        owner's /groups command reflects the whole fleet.
        """
        seen = set()
        if include_bot_id is not None:
            seen.add(include_bot_id)
            self.record_group_membership(include_bot_id, chat_id, chat_title)
        # Main bot (bot_id=0).
        self.record_group_membership(0, chat_id, chat_title)
        # All registered clone bots.
        for row in self.get_bot_instances(only_known=True):
            bid = row.bot_id
            if bid is None or bid in seen:
                continue
            seen.add(bid)
            self.record_group_membership(bid, chat_id, chat_title)

    def remove_group_membership(self, bot_id: int, chat_id: int):
        """Remove a single (bot, chat) membership row."""
        session = self.get_session()
        try:
            session.query(GroupMembership).filter(
                GroupMembership.bot_id == bot_id,
                GroupMembership.chat_id == chat_id,
            ).delete()
            session.commit()
        finally:
            session.close()

    def remove_fleet_membership(self, chat_id: int, bot_id: int):
        """Remove a chat from the fleet registry when a bot leaves it.

        If the leaving bot is the main bot (0) or a clone, we remove the row for
        that bot. A chat is only fully removed once *no* fleet bot is in it.
        """
        # Remove the row for the leaving bot (0 = main bot, else clone).
        self.remove_group_membership(bot_id, chat_id)

        # A chat stays in the fleet registry as long as ANY fleet bot remains a
        # member, so only clean up the main-bot's synthetic row when no clone is
        # still in the chat.
        session = self.get_session()
        try:
            others = session.query(GroupMembership).filter(
                GroupMembership.chat_id == chat_id,
                GroupMembership.bot_id != 0,
            ).count()
        finally:
            session.close()
        if others == 0:
            self.remove_group_membership(0, chat_id)

    def get_fleet_groups(self):
        """Return distinct groups across the fleet with join dates.

        Returns a list of dicts: {chat_id, title, joined_at, bot_ids, enabled_bots}.
        """
        session = self.get_session()
        try:
            rows = session.query(GroupMembership).order_by(
                GroupMembership.chat_id, GroupMembership.joined_at
            ).all()
        finally:
            session.close()

        groups = {}
        for r in rows:
            info = groups.setdefault(r.chat_id, {
                'chat_id': r.chat_id,
                'title': r.chat_title,
                'joined_at': r.joined_at,
                'bot_ids': [],
            })
            if r.bot_id not in info['bot_ids']:
                info['bot_ids'].append(r.bot_id)
            if info['joined_at'] is None or (r.joined_at and r.joined_at < info['joined_at']):
                info['joined_at'] = r.joined_at
        return list(groups.values())

    def get_groups_for_bot(self, bot_id: int):
        """Return GroupMembership rows for a specific bot id (0 = main bot)."""
        session = self.get_session()
        try:
            return session.query(GroupMembership).filter(
                GroupMembership.bot_id == bot_id
            ).order_by(GroupMembership.joined_at.desc()).all()
        finally:
            session.close()


# Global database instance (uses DATABASE_URL; SQLite by default)
db = DatabaseManager()
