from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger
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
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
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

# Global database instance (uses DATABASE_URL; SQLite by default)
db = DatabaseManager()