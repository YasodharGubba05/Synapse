from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import crud
from backend.models.schemas import ChatRequest
from backend.prompts.defaults import CHAT_MODEL, DEFAULT_CHAT_SYSTEM, DEFAULT_DETAIL_SYSTEM
from backend.services.groq_client import iter_groq_chat_stream

router = APIRouter()


def _append_optional_context(system_prompt: str, tag: str, value: str | None) -> str:
    if not value or not value.strip():
        return system_prompt
    return f"{system_prompt}\n\n<{tag}>\n{value.strip()}\n</{tag}>"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    db: Session = Depends(get_db),
):
    words = body.full_transcript.split()[-body.context_window:]
    transcript = " ".join(words)
    model = body.model or CHAT_MODEL

    prompt_template = (
        body.detail_prompt or DEFAULT_DETAIL_SYSTEM
        if body.mode == "suggestion"
        else body.chat_prompt or DEFAULT_CHAT_SYSTEM
    )
    system_prompt = prompt_template.replace("{{FULL_TRANSCRIPT}}", transcript)
    system_prompt = _append_optional_context(system_prompt, "meeting_memory", body.meeting_memory)

    messages = [{"role": "system", "content": system_prompt}]
    for message in body.history:
        messages.append({"role": message.role, "content": message.content})
    messages.append({"role": "user", "content": body.message})

    # Persist user message if session_id provided
    if body.session_id:
        crud.save_chat_message(db, body.session_id, "user", body.message)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 1000,
        "stream": True,
    }

    async def stream_and_save():
        full_response = []
        async for chunk in iter_groq_chat_stream(x_groq_api_key, payload):
            full_response.append(chunk)
            yield chunk
        # Save assistant response to DB
        if body.session_id:
            import json as _json
            combined = "".join(full_response)
            token_text = ""
            for line in combined.split("\n\n"):
                line = line.strip()
                if not line.startswith("data: "):
                    continue
                payload_text = line[6:]
                if payload_text == "[DONE]":
                    continue
                try:
                    parsed = _json.loads(payload_text)
                    token = parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if token:
                        token_text += token
                except Exception:
                    pass
            if token_text:
                crud.save_chat_message(db, body.session_id, "assistant", token_text)

    return StreamingResponse(stream_and_save(), media_type="text/event-stream")
