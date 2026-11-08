import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.connection import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    """An authenticated Synapse account.

    Only the Argon2id password *hash* is ever stored. Groq API keys are never
    persisted here (or anywhere server-side) - they stay in the browser's
    sessionStorage and travel per-request in the X-Groq-API-Key header.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String(320), nullable=False, unique=True, index=True)
    full_name = Column(String(120), nullable=True)
    password_hash = Column(String(512), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    meeting_sessions = relationship(
        "MeetingSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=False,
    )
    auth_sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthSession(Base):
    """A server-side record of one logged-in browser session.

    Access tokens carry this row's id as their `sid` claim, so revoking the
    row (logout, reuse detection, password change) invalidates the still-valid
    access token immediately instead of waiting for it to expire.
    """

    __tablename__ = "auth_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_used_at = Column(DateTime(timezone=True), default=_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    user_agent = Column(String(400), nullable=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", back_populates="auth_sessions")


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    # Nullable so that meetings recorded before authentication existed are
    # preserved; new meetings always carry an owner (enforced in the API).
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False, default="Untitled Meeting")
    playbook = Column(String, nullable=False, default="general")
    started_at = Column(DateTime(timezone=True), default=_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    meeting_memory = Column(Text, default="")
    status = Column(String, default="active")  # active | ended

    user = relationship("User", back_populates="meeting_sessions")
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
