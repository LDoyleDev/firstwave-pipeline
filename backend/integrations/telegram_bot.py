import logging
import os
from typing import Optional

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backend.agents.intent_parser import parse_voice_intent, route_intent
from backend.integrations.groq_client import transcribe_audio

logger = logging.getLogger(__name__)

OPERATOR_CHAT_ID = int(os.getenv("TELEGRAM_OPERATOR_CHAT_ID", "0"))
_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

application: Application = Application.builder().token(_TOKEN).build()

_initialized = False


def _operator_only(func):
    """Decorator: silently ignore messages not from the operator's chat."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or update.effective_chat.id != OPERATOR_CHAT_ID:
            return
        await func(update, context)

    wrapper.__name__ = func.__name__
    return wrapper


@_operator_only
async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "First Wave AI Pipeline\n\n"
        "/pipeline — pipeline status\n"
        "/review — show review queue\n"
        "/next — next meeting briefing\n\n"
        "Or send a voice note."
    )


@_operator_only
async def _cmd_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = route_intent({"intent": "check_pipeline", "parameters": {}, "track": "both"})
    await update.message.reply_text(result.get("message", "Pipeline checked."))


@_operator_only
async def _cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = route_intent({"intent": "review_queue", "parameters": {}, "track": "both"})
    await update.message.reply_text(result.get("message", "Review queue loaded."))


@_operator_only
async def _cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = route_intent({"intent": "pre_meeting_briefing", "parameters": {}, "track": "both"})
    await update.message.reply_text(result.get("message", "No upcoming meetings found."))


@_operator_only
async def _handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice
    if not voice:
        return

    await update.message.reply_text("Transcribing...")

    try:
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = bytes(await tg_file.download_as_bytearray())

        transcript = transcribe_audio(audio_bytes, filename="voice.ogg")
        await update.message.reply_text(f'"{transcript}"')

        intent = parse_voice_intent(transcript)
        result = route_intent(intent)
        await update.message.reply_text(result.get("message", "Done."))

    except Exception:
        logger.exception("Voice handler failed for chat %s", OPERATOR_CHAT_ID)
        await update.message.reply_text("Error processing voice note. Try again.")


@_operator_only
async def _handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    intent = parse_voice_intent(text)
    result = route_intent(intent)
    await update.message.reply_text(result.get("message", "Done."))


application.add_handler(CommandHandler("start", _cmd_start))
application.add_handler(CommandHandler("pipeline", _cmd_pipeline))
application.add_handler(CommandHandler("review", _cmd_review))
application.add_handler(CommandHandler("next", _cmd_next))
application.add_handler(MessageHandler(filters.VOICE, _handle_voice))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))


async def process_webhook_update(data: dict) -> None:
    """Process a Telegram webhook update payload. Called from the FastAPI webhook endpoint."""
    global _initialized
    if not _initialized:
        await application.initialize()
        _initialized = True

    update = Update.de_json(data, application.bot)
    await application.process_update(update)


async def send_operator_message(text: str, chat_id: Optional[int] = None) -> None:
    """Send a message to the operator (or a specific chat_id). Fire-and-forget helper."""
    target = chat_id or OPERATOR_CHAT_ID
    async with Bot(token=_TOKEN) as bot:
        await bot.send_message(chat_id=target, text=text)
