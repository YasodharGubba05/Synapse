from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import crud
from backend.models.schemas import (
    MeetingStartRequest, MeetingStartResponse,
    MeetingEndRequest, MeetingEndResponse,
)

router = APIRouter()


@router.post("/meeting/start", response_model=MeetingStartResponse)
async def start_meeting(
    body: MeetingStartRequest,
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    db: Session = Depends(get_db),
):
    del x_groq_api_key
    session = crud.create_session(
        db,
        playbook=body.playbook or "general",
        meeting_memory=body.meeting_memory or "",
    )
    if body.title and body.title != "Untitled Meeting":
        crud.update_session_title(db, session.id, body.title)
        db.refresh(session)
    return MeetingStartResponse(
        session_id=session.id,
        started_at=session.started_at.isoformat(),
        status=session.status,
    )


@router.post("/meeting/end", response_model=MeetingEndResponse)
async def end_meeting(
    body: MeetingEndRequest,
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    db: Session = Depends(get_db),
):
    del x_groq_api_key
    session = crud.end_session(db, body.session_id)
    ended_at = session.ended_at.isoformat() if session and session.ended_at else datetime.now(timezone.utc).isoformat()
    return MeetingEndResponse(
        session_id=body.session_id,
        ended_at=ended_at,
        status="ended",
    )
