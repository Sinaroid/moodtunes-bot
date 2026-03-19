import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import get_effective_lang, search_songs, get_all_songs, log_play
from ai_analyzer import find_best_match
from strings import t
from utils import make_song_keyboard, make_audio_caption, make_voice_error_keyboard, make_not_found_keyboard

logger = logging.getLogger(__name__)

try:
    import whisper
    _WHISPER_MODEL = None  # lazy-loaded on first use

    def _get_whisper_model():
        global _WHISPER_MODEL
        if _WHISPER_MODEL is None:
            _WHISPER_MODEL = whisper.load_model("base")
        return _WHISPER_MODEL

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("openai-whisper not installed — voice messages disabled.")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe voice → text search."""
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)

    if not WHISPER_AVAILABLE:
        await update.message.reply_text(
            t("err_voice_failed", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_voice_error_keyboard(lang),
        )
        return

    status = await update.message.reply_text(t("voice_processing", lang))

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await file.download_to_drive(tmp_path)
        model = _get_whisper_model()
        result = model.transcribe(tmp_path, fp16=False)
        text = result.get("text", "").strip()
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}", exc_info=True)
        await status.edit_text(
            t("err_voice_failed", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_voice_error_keyboard(lang),
        )
        return
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not text:
        await status.edit_text(
            t("err_voice_failed", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_voice_error_keyboard(lang),
        )
        return

    await status.edit_text(
        t("voice_transcribed", lang, text=text),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # Search the DB
        results = await search_songs(text)
        if results:
            song = results[0]
            found_text = "پیداش کردم! 🎉" if lang == "fa" else "Found it! 🎉"
            try:
                await update.message.reply_text(found_text)
                await update.message.reply_audio(
                    audio=song["file_id"],
                    caption=make_audio_caption(song["title"], song["artist"]),
                    reply_markup=make_song_keyboard(song["id"], lang),
                )
                await log_play(user_id, song["id"])
            except Exception as e:
                logger.error(f"Error sending voice search result: {e}")
            return

        # AI fallback
        all_songs = await get_all_songs()
        if not all_songs:
            await update.message.reply_text(
                t("err_db_empty", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_voice_error_keyboard(lang),
            )
            return

        try:
            best = await find_best_match(text, all_songs)
        except Exception as e:
            logger.error(f"Voice AI match error: {e}", exc_info=True)
            await update.message.reply_text(
                t("err_api_busy", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_voice_error_keyboard(lang),
            )
            return

        if best:
            try:
                await update.message.reply_audio(
                    audio=best["file_id"],
                    caption=make_audio_caption(best["title"], best["artist"]),
                    reply_markup=make_song_keyboard(best["id"], lang),
                )
                await log_play(user_id, best["id"])
            except Exception as e:
                logger.error(f"Error sending voice AI match: {e}")
        else:
            await update.message.reply_text(
                t("err_not_found", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_not_found_keyboard(lang),
            )

    except Exception as e:
        logger.error(f"Unhandled error in handle_voice_message: {e}", exc_info=True)
        await update.message.reply_text(
            t("err_general", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_voice_error_keyboard(lang),
        )
