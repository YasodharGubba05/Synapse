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
    try:
        audio_bytes = await audio_file.read()
        if not audio_bytes:
            return {"text": ""}

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
        return {"text": result.get("text", "")}
    except HTTPException as exc:
        detail = str(exc.detail)
        if exc.status_code == 400 and "could not process file" in detail:
            logger.warning("Skipping undecodable audio chunk (%s bytes, %s)", len(audio_bytes), audio_file.content_type)
        else:
            logger.exception("Transcription request failed")
        return {"text": ""}
    except Exception:
        logger.exception("Transcription failed")
        return {"text": ""}
