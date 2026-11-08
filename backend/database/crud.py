from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.database.models import (
    MeetingSession, TranscriptEntry, SuggestionItem,
    ChatMessage, ActionItem, DecisionItem,
    AuthSession, User,
)


def _now():
    return datetime.now(timezone.utc)


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(
    db: Session,
    user_id: str,
    playbook: str = "general",
    meeting_memory: str = "",
) -> MeetingSession:
    session = MeetingSession(user_id=user_id, playbook=playbook, meeting_memory=meeting_memory)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> Optional[MeetingSession]:
    return db.query(MeetingSession).filter(MeetingSession.id == session_id).first()


def get_owned_session(db: Session, session_id: str, user_id: str) -> Optional[MeetingSession]:
    """Fetch a session only if it belongs to `user_id`."""
    return (
        db.query(MeetingSession)
        .filter(MeetingSession.id == session_id, MeetingSession.user_id == user_id)
        .first()
    )


def list_sessions(db: Session, user_id: str):
    return (
        db.query(MeetingSession)
        .filter(MeetingSession.user_id == user_id)
        .order_by(MeetingSession.started_at.desc())
        .all()
    )


def end_session(db: Session, session_id: str) -> Optional[MeetingSession]:
    s = get_session(db, session_id)
    if s:
        s.ended_at = _now()
        s.status = "ended"
        db.commit()
        db.refresh(s)
    return s


def update_session_title(db: Session, session_id: str, title: str) -> Optional[MeetingSession]:
    s = get_session(db, session_id)
    if s:
        s.title = title
        db.commit()
        db.refresh(s)
    return s


def delete_session(db: Session, session_id: str) -> bool:
    s = get_session(db, session_id)
    if s:
        db.delete(s)
        db.commit()
        return True
    return False


# ── Transcript ────────────────────────────────────────────────────────────────

def save_transcript_entry(db: Session, session_id: str, time_label: str, iso_time: str, text: str, kind: str = "speech"):
    entry = TranscriptEntry(session_id=session_id, time_label=time_label, iso_time=iso_time, text=text, kind=kind)
    db.add(entry)
    db.commit()
    return entry


# ── Suggestions ───────────────────────────────────────────────────────────────

def save_suggestion(db: Session, session_id: str, type_: str, title: str, preview: str):
    item = SuggestionItem(session_id=session_id, type=type_, title=title, preview=preview)
    db.add(item)
    db.commit()
    return item


# ── Chat ──────────────────────────────────────────────────────────────────────

def save_chat_message(db: Session, session_id: str, role: str, content: str):
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    return msg


# ── Action Items ──────────────────────────────────────────────────────────────

def save_action_item(db: Session, session_id: str, task: str, assignee: Optional[str] = None, priority: str = "medium"):
    item = ActionItem(session_id=session_id, task=task, assignee=assignee, priority=priority)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_action_item_status(
    db: Session, item_id: str, status: str, session_id: Optional[str] = None
) -> Optional[ActionItem]:
    """Update an action item. When `session_id` is given the item must belong
    to that session, which keeps the lookup inside the caller's own data."""
    query = db.query(ActionItem).filter(ActionItem.id == item_id)
    if session_id is not None:
        query = query.filter(ActionItem.session_id == session_id)
    item = query.first()
    if item:
        item.status = status
        db.commit()
        db.refresh(item)
    return item


def delete_action_item(db: Session, item_id: str, session_id: Optional[str] = None) -> bool:
    query = db.query(ActionItem).filter(ActionItem.id == item_id)
    if session_id is not None:
        query = query.filter(ActionItem.session_id == session_id)
    item = query.first()
    if item:
        db.delete(item)
        db.commit()
        return True
    return False


# ── Decisions ─────────────────────────────────────────────────────────────────

def save_decision(db: Session, session_id: str, content: str):
    item = DecisionItem(session_id=session_id, content=content)
    db.add(item)
    db.commit()
    return item


# ── Users & auth sessions ─────────────────────────────────────────────────────

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == normalize_email(email)).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, password_hash: str, full_name: Optional[str] = None) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_auth_session(
    db: Session,
    user_id: str,
    refresh_token_hash: str,
    expires_at,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
        user_agent=(user_agent or "")[:400] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    return auth_session


def get_auth_session(db: Session, auth_session_id: str) -> Optional[AuthSession]:
    return db.query(AuthSession).filter(AuthSession.id == auth_session_id).first()


def rotate_auth_session(db: Session, auth_session: AuthSession, refresh_token_hash: str, expires_at) -> AuthSession:
    auth_session.refresh_token_hash = refresh_token_hash
    auth_session.expires_at = expires_at
    auth_session.last_used_at = _now()
    db.commit()
    db.refresh(auth_session)
    return auth_session


def revoke_auth_session(db: Session, auth_session: AuthSession) -> None:
    if auth_session.revoked_at is None:
        auth_session.revoked_at = _now()
        db.commit()


def revoke_all_auth_sessions(db: Session, user_id: str) -> int:
    rows = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .all()
    )
    now = _now()
    for row in rows:
        row.revoked_at = now
    if rows:
        db.commit()
    return len(rows)


def purge_expired_auth_sessions(db: Session) -> int:
    deleted = (
        db.query(AuthSession)
        .filter(AuthSession.expires_at < _now())
        .delete(synchronize_session=False)
    )
    if deleted:
        db.commit()
    return deleted


def record_successful_login(db: Session, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _now()
    db.commit()


def record_failed_login(db: Session, user: User, max_failures: int, lock_minutes: int) -> None:
    from datetime import timedelta

    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= max_failures:
        user.locked_until = _now() + timedelta(minutes=lock_minutes)
        user.failed_login_count = 0
    db.commit()


def update_password_hash(db: Session, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    db.commit()
