"""Live Groq model catalogue for the Settings dropdown.

Groq retires model IDs on a schedule and a retired ID returns 404, so a
hardcoded list silently rots. This asks Groq what the caller's own key can
actually use right now.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.exceptions import HTTPException as FastAPIHTTPException

from backend.database.models import User
from backend.dependencies import get_current_user
from backend.prompts.defaults import CHAT_MODEL, SUGGESTIONS_MODEL
from backend.services.groq_client import groq_get

router = APIRouter()
logger = logging.getLogger(__name__)

# Models that exist but are not chat-completion models.
_NON_CHAT_HINTS = ("whisper", "tts", "guard", "embed", "orpheus")


def _is_chat_model(model_id: str) -> bool:
    lowered = model_id.lower()
    return not any(hint in lowered for hint in _NON_CHAT_HINTS)


@router.get("/models")
async def list_models(
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    user: User = Depends(get_current_user),
):
    """Chat models the caller's Groq account can use, newest-looking first."""
    del user
    try:
        payload = await groq_get("/models", x_groq_api_key)
    except FastAPIHTTPException as exc:
        logger.warning("Could not list Groq models: HTTP %s", exc.status_code)
        raise HTTPException(
            status_code=exc.status_code,
            detail="Could not load the model list from Groq.",
        ) from exc

    models = [
        {"value": entry["id"], "label": entry["id"]}
        for entry in payload.get("data", [])
        if entry.get("id") and _is_chat_model(entry["id"])
    ]
    models.sort(key=lambda m: m["value"])
    return {
        "models": models,
        "defaults": {"suggestions": SUGGESTIONS_MODEL, "chat": CHAT_MODEL},
    }
