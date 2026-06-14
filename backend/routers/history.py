from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import crud
from backend.models.schemas import (
    SessionSummary, SessionDetail, UpdateTitleRequest, ActionItemStatusRequest
)

router = APIRouter()


def _serialize_session_summary(s) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "playbook": s.playbook,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "status": s.status,
        "transcript_count": len(s.transcript_entries),
        "action_item_count": len(s.action_items),
    }


def _serialize_session_detail(s) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "playbook": s.playbook,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "status": s.status,
        "meeting_memory": s.meeting_memory or "",
        "transcript_entries": [
            {"time": e.time_label, "isoTime": e.iso_time, "text": e.text, "kind": e.kind}
            for e in s.transcript_entries
        ],
        "suggestions": [
            {"type": sg.type, "title": sg.title, "preview": sg.preview}
            for sg in s.suggestions
        ],
        "chat_messages": [
            {"role": m.role, "content": m.content}
            for m in s.chat_messages
        ],
        "action_items": [
            {"id": a.id, "task": a.task, "assignee": a.assignee, "priority": a.priority, "status": a.status}
            for a in s.action_items
        ],
        "decisions": [
            {"id": d.id, "content": d.content}
            for d in s.decisions
        ],
    }


@router.get("/history")
def list_history(db: Session = Depends(get_db)):
    sessions = crud.list_sessions(db)
    return [_serialize_session_summary(s) for s in sessions]


@router.get("/history/{session_id}")
def get_history_session(session_id: str, db: Session = Depends(get_db)):
    s = crud.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session_detail(s)


@router.put("/history/{session_id}/title")
def update_title(session_id: str, body: UpdateTitleRequest, db: Session = Depends(get_db)):
    s = crud.update_session_title(db, session_id, body.title)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": s.id, "title": s.title}


@router.delete("/history/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    deleted = crud.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.patch("/history/{session_id}/actions/{item_id}")
def patch_action_item(session_id: str, item_id: str, body: ActionItemStatusRequest, db: Session = Depends(get_db)):
    item = crud.update_action_item_status(db, item_id, body.status)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return {"id": item.id, "status": item.status}


@router.delete("/history/{session_id}/actions/{item_id}")
def delete_action_item(session_id: str, item_id: str, db: Session = Depends(get_db)):
    deleted = crud.delete_action_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Action item not found")
    return {"deleted": True}
