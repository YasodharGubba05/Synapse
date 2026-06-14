import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import crud
from backend.models.schemas import IntelligenceRequest, IntelligenceResponse
from backend.prompts.defaults import INTELLIGENCE_MODEL, INTELLIGENCE_SYSTEM_PROMPT
from backend.services.groq_client import groq_post

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/intelligence", response_model=IntelligenceResponse)
async def get_intelligence(
    body: IntelligenceRequest,
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    db: Session = Depends(get_db),
):
    words = body.transcript_slice.split()[-body.context_window:]
    transcript_slice = " ".join(words)
    model = body.model or INTELLIGENCE_MODEL

    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": INTELLIGENCE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n<transcript>\n{transcript_slice}\n</transcript>\n\nReturn JSON now."},
        ],
    }

    try:
        result = await groq_post("/chat/completions", x_groq_api_key, payload)
    except HTTPException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    raw = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

    try:
        data = json.loads(raw)
        response = IntelligenceResponse(
            sentiment=data.get("sentiment", "neutral"),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            keywords=data.get("keywords", []),
        )
    except Exception as exc:
        logger.warning("Intelligence parse failed: %s", exc)
        response = IntelligenceResponse(sentiment="neutral", action_items=[], decisions=[], keywords=[])

    # Persist to DB if session_id is provided
    if body.session_id:
        for item in response.action_items:
            crud.save_action_item(
                db, body.session_id,
                task=item.task,
                assignee=item.assignee,
                priority=item.priority,
            )
        for decision in response.decisions:
            crud.save_decision(db, body.session_id, decision)

    return response
