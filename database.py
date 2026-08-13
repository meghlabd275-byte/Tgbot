from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from config import Config

Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(255))
    is_active = Column(Boolean, default=False)
    is_silenced = Column(Boolean, default=False)
    under_attack = Column(Boolean, default=False)
    pinned_message_id = Column(Integer)
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

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
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
            if user_id == Config.SUPER_ADMIN_ID:
                return True
            
            query = session.query(Admin).filter(Admin.user_id == user_id)
            if chat_id:
                query = query.filter(Admin.chat_id == chat_id)
            
            return query.first() is not None
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
    
    def add_mute(self, user_id: int, chat_id: int, muted_by: int, duration: int, reason: str = None):
        """Add a mute record"""
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
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
        """Remove mute record"""
        session = self.get_session()
        try:
            mute = session.query(Mute).filter(
                Mute.user_id == user_id,
                Mute.chat_id == chat_id
            ).first()
            
            if mute:
                session.delete(mute)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def is_muted(self, user_id: int, chat_id: int):
        """Check if user is currently muted"""
        session = self.get_session()
        try:
            from datetime import datetime
            mute = session.query(Mute).filter(
                Mute.user_id == user_id,
                Mute.chat_id == chat_id,
                Mute.until > datetime.now()
            ).first()
            
            return mute is not None
        finally:
            session.close()

# Global database instance
db = DatabaseManager(Config.DATABASE_URL)