from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.sqlite import INTEGER, TEXT, BOOLEAN
import datetime, uuid


Base = declarative_base() # Базовый класс модели

# Прослушиваемый канал
class ListeningChannel(Base):
    __tablename__ = 'listening_channels'
    
    # Столбцы
    listening_channel_id = Column(INTEGER, primary_key=True) 
    tg_chat_id = Column(INTEGER, unique=True, nullable=False)
    title = Column(TEXT, nullable=False)
    enabled = Column(BOOLEAN, nullable=False, default=True)
    
    # Связи
    notified_users = relationship('NotifiedUser', back_populates='listening_channel', cascade='all, delete-orphan')
    
    # Конструктор
    def __init__(self, tg_chat_id: int, title: str):
        self.tg_chat_id = tg_chat_id
        self.title = title

    # Преобразование в строку
    def __repr__(self):
        return f"<ListeningChannel({self.listening_channel_id}, {self.title})>"


# Пользователь
class User(Base):
    __tablename__ = 'users'

    # Столбцы
    user_id = Column(INTEGER, primary_key=True)
    tg_user_id = Column(INTEGER, unique=True, nullable=False)
    name = Column(TEXT, nullable=False)
    
    # Связи
    notified_users = relationship('NotifiedUser', back_populates='user', cascade='all, delete-orphan')

    # Конструктор
    def __init__(self, tg_user_id: int, name: str):
        self.tg_user_id = tg_user_id
        self.name = name

    # Преобразование в строку
    def __repr__(self):
        return f"<User({self.user_id}, {self.name})>"
    

# Уведомляемый пользователь
class NotifiedUser(Base):
    __tablename__ = 'notified_users'

    # Столбцы
    notified_user_id = Column(INTEGER, primary_key=True)
    user_id = Column(ForeignKey('users.user_id'), nullable=False)
    listening_channel_id = Column(ForeignKey("listening_channels.listening_channel_id"), nullable=False)
    notifications_enabled = Column(BOOLEAN, nullable=False, default=True)
    
    # Связи
    user = relationship('User', back_populates='notified_users')
    listening_channel = relationship('ListeningChannel', back_populates='notified_users')
    
    # Конструктор
    def __init__(self, user_id: int, listening_channel_id: str):
        self.user_id = user_id
        self.listening_channel_id = listening_channel_id

    # Преобразование в строку
    def __repr__(self):
        return f"<NotifiedUser({self.notified_user_id})>"
