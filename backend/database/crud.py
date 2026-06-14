from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.database.models import (
    MeetingSession, TranscriptEntry, SuggestionItem,
    ChatMessage, ActionItem, DecisionItem,
)


def _now():
    return datetime.now(timezone.utc)


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(db: Session, playbook: str = "general", meeting_memory: str = "") -> MeetingSession:
    session = MeetingSession(playbook=playbook, meeting_memory=meeting_memory)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> Optional[MeetingSession]:
    return db.query(MeetingSession).filter(MeetingSession.id == session_id).first()


def list_sessions(db: Session):
    return db.query(MeetingSession).order_by(MeetingSession.started_at.desc()).all()


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


def update_action_item_status(db: Session, item_id: str, status: str) -> Optional[ActionItem]:
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if item:
        item.status = status
        db.commit()
        db.refresh(item)
    return item


def delete_action_item(db: Session, item_id: str) -> bool:
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
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
