import logging

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram webhook updates and dispatch to the bot handlers.

    Always returns HTTP 200 so Telegram does not retry on processing errors.
    """
    from backend.integrations.telegram_bot import process_webhook_update

    try:
        data = await request.json()
        await process_webhook_update(data)
        return {"ok": True}
    except Exception as e:
        logger.exception("Telegram webhook processing error: %s", e)
        return {"ok": False, "error": str(e)}


class VoiceFeedbackResponse(BaseModel):
    meeting_id: str
    transcript: str
    outcome: str
    next_action: str
    next_action_at: str
    follow_up_draft: str


@router.post("/voice/feedback", response_model=VoiceFeedbackResponse)
async def voice_feedback(
    meeting_id: str = Form(...),
    audio: UploadFile = File(...),
) -> VoiceFeedbackResponse:
    """Receive a post-meeting voice note, transcribe it, and generate a follow-up draft.

    Expects multipart/form-data with:
      - meeting_id: UUID of the meeting record
      - audio: Audio file (OGG, WAV, MP3 — OGG is what Telegram sends)

    Returns the transcript plus the follow-up draft for review before sending.
    """
    from backend.integrations.groq_client import transcribe_audio
    from backend.agents.followup import generate_followup

    audio_bytes = await audio.read()
    filename = audio.filename or "feedback.ogg"

    transcript = transcribe_audio(audio_bytes, filename)

    try:
        result = generate_followup(meeting_id, transcript)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return VoiceFeedbackResponse(
        meeting_id=meeting_id,
        transcript=transcript,
        outcome=result.get("outcome", ""),
        next_action=result.get("next_action", ""),
        next_action_at=result.get("next_action_at", ""),
        follow_up_draft=result.get("follow_up_draft", ""),
    )
