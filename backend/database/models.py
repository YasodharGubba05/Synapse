import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False, default="Untitled Meeting")
    playbook = Column(String, nullable=False, default="general")
    started_at = Column(DateTime(timezone=True), default=_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    meeting_memory = Column(Text, default="")
    status = Column(String, default="active")  # active | ended

    transcript_entries = relationship("TranscriptEntry", back_populates="session", cascade="all, delete-orphan")
    suggestions = relationship("SuggestionItem", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="session", cascade="all, delete-orphan")
    decisions = relationship("DecisionItem", back_populates="session", cascade="all, delete-orphan")


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("meeting_sessions.id"), nullable=False)
    time_label = Column(String)
    iso_time = Column(String)
    text = Column(Text)
    kind = Column(String, default="speech")  # speech | silence
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("MeetingSession", back_populates="transcript_entries")


class SuggestionItem(Base):
    __tablename__ = "suggestion_items"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("meeting_sessions.id"), nullable=False)
    type = Column(String)
    title = Column(String)
    preview = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("MeetingSession", back_populates="suggestions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("meeting_sessions.id"), nullable=False)
    role = Column(String)  # user | assistant
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("MeetingSession", back_populates="chat_messages")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("meeting_sessions.id"), nullable=False)
    task = Column(Text)
    assignee = Column(String, nullable=True)
    priority = Column(String, default="medium")  # high | medium | low
    status = Column(String, default="pending")  # pending | completed
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("MeetingSession", back_populates="action_items")


class DecisionItem(Base):
    __tablename__ = "decision_items"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("meeting_sessions.id"), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("MeetingSession", back_populates="decisions")
