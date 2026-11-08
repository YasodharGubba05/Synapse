import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import crud
from backend.database.models import User
from backend.dependencies import get_current_user, require_owned_session
from backend.models.schemas import Suggestion, SuggestionRequest, SuggestionsResponse
from backend.prompts.defaults import PLAYBOOK_PROMPTS, SUGGESTIONS_MODEL
from backend.services.groq_client import groq_post

router = APIRouter()


def _parse_suggestions(raw: str) -> list[Suggestion]:
    parsed = json.loads(raw)
    items = parsed if isinstance(parsed, list) else parsed.get("suggestions", [])
    suggestions = [Suggestion(**item) for item in items[:3]]
    if len(suggestions) != 3:
        raise ValueError(f"Expected exactly 3 suggestions, received {len(suggestions)}")
    return suggestions


def _build_optional_context_block(tag: str, value: str | None) -> str:
    if not value or not value.strip():
        return ""
    return f"\n<{tag}>\n{value.strip()}\n</{tag}>\n"


def _build_user_message(transcript_slice, latest_transcript_chunk, meeting_memory, previous_suggestions, silence_streak_count):
    return (
        "Recent transcript:\n"
        f"<transcript>\n{transcript_slice}\n</transcript>\n"
        f"{_build_optional_context_block('latest_chunk', latest_transcript_chunk)}"
        f"{_build_optional_context_block('meeting_memory', meeting_memory)}"
        f"{_build_optional_context_block('previous_suggestions', json.dumps(previous_suggestions, ensure_ascii=True))}"
        f"{_build_optional_context_block('silence_streak_count', str(silence_streak_count or 0))}"
        "\nReturn exactly 3 suggestions now."
    )


@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    body: SuggestionRequest,
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.session_id:
        require_owned_session(db, user, body.session_id)

    words = body.transcript_slice.split()[-body.context_window:]
    transcript_slice = " ".join(words)
    previous_suggestions = [item.strip() for item in body.previous_suggestions if item.strip()][:6]

    # Pick playbook prompt or custom prompt
    playbook_key = (body.playbook or "general").lower()
    system_prompt = body.suggestions_prompt or PLAYBOOK_PROMPTS.get(playbook_key, PLAYBOOK_PROMPTS["general"])
    model = body.model or SUGGESTIONS_MODEL
    user_message = _build_user_message(
        transcript_slice, body.latest_transcript_chunk,
        body.meeting_memory, previous_suggestions, body.silence_streak_count,
    )

    last_error = None
    attempts = [
        {"user_message": user_message, "max_tokens": 600, "response_format": {"type": "json_object"}},
        {
            "user_message": f"{user_message}\n\nYour previous answer was invalid. Return only compact JSON.",
            "max_tokens": 450,
            "response_format": {"type": "json_object"},
        },
        {
            "user_message": _build_user_message(
                " ".join(transcript_slice.split()[-450:]), body.latest_transcript_chunk,
                body.meeting_memory if body.meeting_memory and len(body.meeting_memory) < 1200 else None,
                previous_suggestions[:3], body.silence_streak_count,
            ),
            "max_tokens": 350,
            "response_format": None,
        },
    ]

    for attempt in attempts:
        payload = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": attempt["max_tokens"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": attempt["user_message"]},
            ],
        }
        if attempt["response_format"] is not None:
            payload["response_format"] = attempt["response_format"]

        try:
            result = await groq_post("/chat/completions", x_groq_api_key, payload)
        except HTTPException as exc:
            last_error = exc
            continue

        raw = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            suggestions = _parse_suggestions(raw)
            # Persist suggestions to DB if session_id provided
            if body.session_id:
                for s in suggestions:
                    crud.save_suggestion(db, body.session_id, s.type, s.title, s.preview)
            return SuggestionsResponse(suggestions=suggestions)
        except Exception as exc:
            last_error = exc

    raise HTTPException(status_code=500, detail="Unable to generate suggestions right now.") from last_error
