import asyncio
import os
import platform
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text

DATABASE_URL = "sqlite+aiosqlite:///./netmanager.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    ip          = Column(String(45), nullable=False, unique=True)
    hostname    = Column(String(200), default="")
    group_name  = Column(String(100), default="General")
    device_type = Column(String(50), default="Workstation")
    notes       = Column(Text, default="")
    enabled     = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class PingHistory(Base):
    __tablename__ = "ping_history"
    id         = Column(Integer, primary_key=True, index=True)
    device_id  = Column(Integer, nullable=False)
    ip         = Column(String(45), nullable=False)
    status     = Column(String(10), nullable=False)   # UP / DOWN
    latency_ms = Column(Float, default=0.0)
    timestamp  = Column(DateTime, default=datetime.utcnow)


class AnydeskLog(Base):
    __tablename__ = "anydesk_logs"
    id        = Column(Integer, primary_key=True, index=True)
    level     = Column(String(20), default="INFO")
    message   = Column(Text, nullable=False)
    source    = Column(String(100), default="anydesk")
    timestamp = Column(DateTime, default=datetime.utcnow)


class AlertRecord(Base):
    __tablename__ = "alert_records"
    id           = Column(Integer, primary_key=True, index=True)
    device_id    = Column(Integer, nullable=True)
    device_name  = Column(String(100), default="")
    alert_type   = Column(String(50), nullable=False)
    message      = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)


class SavedRemote(Base):
    __tablename__ = "saved_remotes"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)          # friendly label
    anydesk_id  = Column(String(100), nullable=False)          # AnyDesk ID or alias
    description = Column(Text, default="")
    group_name  = Column(String(100), default="General")
    created_at  = Column(DateTime, default=datetime.utcnow)


class RemoteSession(Base):
    __tablename__ = "remote_sessions"
    id          = Column(Integer, primary_key=True, index=True)
    anydesk_id  = Column(String(100), nullable=False)
    label       = Column(String(100), default="")
    status      = Column(String(20), default="launched")       # launched / error
    error_msg   = Column(Text, default="")
    started_at  = Column(DateTime, default=datetime.utcnow)


class RemoteSessionConfig(Base):
    __tablename__ = "remote_session_configs"
    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False)        # friendly label
    session_type = Column(String(10), nullable=False)         # ssh | vnc
    host         = Column(String(200), nullable=False)
    port         = Column(Integer, nullable=False)            # 22 for SSH, 5900 for VNC
    username     = Column(String(100), default="")            # SSH username
    password     = Column(String(255), default="")            # SSH pass or VNC pass
    ssh_key      = Column(Text, default="")                   # Private key PEM (optional)
    group_name   = Column(String(100), default="General")
    notes        = Column(Text, default="")
    created_at   = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
