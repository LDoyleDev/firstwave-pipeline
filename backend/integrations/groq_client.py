import io
import os
import logging

from groq import Groq

logger = logging.getLogger(__name__)

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

_MIME_TYPES = {
    "ogg": "audio/ogg",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "webm": "audio/webm",
    "flac": "audio/flac",
}


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribe audio bytes using Groq Whisper large-v3.

    Args:
        audio_bytes: Raw audio bytes. OGG (Telegram voice), WAV, MP3, etc. all supported.
        filename: Filename hint used to infer MIME type for the API request.

    Returns:
        Transcript text.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"
    mime = _MIME_TYPES.get(ext, "audio/ogg")

    transcription = _client.audio.transcriptions.create(
        file=(filename, io.BytesIO(audio_bytes), mime),
        model="whisper-large-v3",
    )

    text = transcription.text if hasattr(transcription, "text") else str(transcription)
    logger.info("Groq transcribed %d bytes → %d chars", len(audio_bytes), len(text))
    return text
