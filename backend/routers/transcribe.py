import logging

from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.exceptions import HTTPException

from backend.config import settings
from backend.database.models import User
from backend.dependencies import get_current_user
from backend.prompts.defaults import TRANSCRIPTION_MODEL
from backend.services.groq_client import groq_post_multipart, redact_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

MIN_AUDIO_BYTES = 500
ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/ogg", "audio/mp4", "audio/x-m4a", "audio/mpeg",
    "audio/wav", "audio/x-wav", "audio/mpga", "audio/m4a", "audio/flac",
    "application/octet-stream",
}


async def _read_capped(audio_file: UploadFile, cap: int) -> bytes | None:
    """Read at most `cap` bytes; return None when the upload exceeds the cap.

    Reading in chunks means an oversized upload is rejected without buffering
    the whole body in memory first.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await audio_file.read(1024 * 256)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    x_groq_api_key: str = Header(..., alias="X-Groq-API-Key"),
    user: User = Depends(get_current_user),
):
    audio_bytes = b""
    try:
        capped = await _read_capped(audio_file, settings.max_upload_bytes)
        if capped is None:
            limit_mb = settings.max_upload_bytes // (1024 * 1024)
            logger.warning("Audio blob rejected: exceeds %s MB cap", limit_mb)
            return {"text": "", "error": f"Audio file too large (max {limit_mb} MB)"}
        audio_bytes = capped

        logger.info(
            "Transcription request: user=%s size=%s content_type=%s",
            user.id, len(audio_bytes), audio_file.content_type,
        )

        if not audio_bytes or len(audio_bytes) < MIN_AUDIO_BYTES:
            logger.warning("Skipping tiny/empty audio blob: %s bytes", len(audio_bytes))
            return {"text": ""}

        content_type = (audio_file.content_type or "audio/webm").split(";")[0].strip().lower()
        if content_type not in ALLOWED_AUDIO_TYPES:
            logger.warning("Rejected unsupported audio content type: %r", content_type)
            return {"text": "", "error": "Unsupported audio format"}

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
        logger.info("Transcription OK: %s characters", len(text))
        return {"text": text}

    except HTTPException as exc:
        # Redact here as well as in groq_client: this string is both logged
        # and returned to the browser.
        detail = redact_api_key(str(exc.detail), x_groq_api_key)
        logger.warning(
            "Groq transcription HTTP %s - %s (bytes=%s type=%s)",
            exc.status_code, detail[:400],
            len(audio_bytes), audio_file.content_type,
        )
        return {"text": "", "error": detail[:200]}
    except Exception:
        logger.exception(
            "Transcription failed unexpectedly (bytes=%s)", len(audio_bytes),
        )
        return {"text": ""}
