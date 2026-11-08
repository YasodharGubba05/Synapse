import logging

from fastapi import APIRouter, File, Header, UploadFile
from fastapi.exceptions import HTTPException

from backend.prompts.defaults import TRANSCRIPTION_MODEL
from backend.services.groq_client import groq_post_multipart

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
):
    audio_bytes = b""
    try:
        audio_bytes = await audio_file.read()
        logger.info(
            "Transcription request: filename=%s size=%s content_type=%s",
            audio_file.filename, len(audio_bytes), audio_file.content_type,
        )

        if not audio_bytes or len(audio_bytes) < 500:
            logger.warning("Skipping tiny/empty audio blob: %s bytes", len(audio_bytes))
            return {"text": ""}

        if len(audio_bytes) > 25 * 1024 * 1024:
            logger.warning("Audio blob too large: %s bytes", len(audio_bytes))
            return {"text": "", "error": "Audio file too large (max 25 MB)"}

        content_type = (audio_file.content_type or "audio/webm").split(";")[0].strip().lower()

        result = await groq_post_multipart(
            api_key=x_groq_api_key,
            files={
                "file": (
                    audio_file.filename or "audio.webm",
                    audio_bytes,
                    content_type,
                )
            },
            data={"model": TRANSCRIPTION_MODEL, "response_format": "json"},
        )
        text = result.get("text", "")
        logger.info("Transcription OK: %r", (text[:100] + "…") if len(text) > 100 else text)
        return {"text": text}

    except HTTPException as exc:
        detail = str(exc.detail)
        logger.warning(
            "Groq transcription HTTP %s — %s (file=%s bytes=%s type=%s)",
            exc.status_code, detail[:400],
            audio_file.filename, len(audio_bytes), audio_file.content_type,
        )
        return {"text": "", "error": detail[:200]}
    except Exception:
        logger.exception(
            "Transcription failed unexpectedly (file=%s bytes=%s)",
            audio_file.filename, len(audio_bytes),
        )
        return {"text": ""}
