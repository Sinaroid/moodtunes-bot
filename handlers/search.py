import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import search_songs, get_all_songs, log_play, get_effective_lang, get_song_by_id, get_songs_by_mood
from ai_analyzer import find_best_match, detect_mood_from_text
from strings import t
from utils import make_song_keyboard, make_audio_caption, make_not_found_keyboard

logger = logging.getLogger(__name__)

# ConversationHandler states
SEARCH_WAITING_QUERY = 0


async def _show_inline_results(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Show DB search results as inline buttons (used by home Search button)."""
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)
    results = await search_songs(query)
    if not results:
        await update.message.reply_text(
            t("err_not_found", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_not_found_keyboard(lang),
        )
        return
    await update.message.reply_text(
        t("search_results_header", lang, query=query),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                t("search_btn_play", lang, title=s["title"], artist=s["artist"]),
                callback_data=f"search_play:{s['id']}"
            )]
            for s in results[:8]
        ])
    )


# ── /search ConversationHandler ───────────────────────────────────────────────

async def cmd_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry: /search → ask for query."""
    lang = await get_effective_lang(update.effective_user.id)
    await update.message.reply_text(t("search_prompt", lang), parse_mode=ParseMode.MARKDOWN)
    return SEARCH_WAITING_QUERY


async def cmd_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive search text, show inline button results."""
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)
    query = update.message.text.strip()

    try:
        results = await search_songs(query)
    except Exception as e:
        logger.error(f"Search DB error: {e}", exc_info=True)
        await update.message.reply_text(
            t("err_general", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_not_found_keyboard(lang),
        )
        return ConversationHandler.END

    if not results:
        await update.message.reply_text(
            t("err_not_found", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_not_found_keyboard(lang),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        t("search_results_header", lang, query=query),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                t("search_btn_play", lang, title=s["title"], artist=s["artist"]),
                callback_data=f"search_play:{s['id']}"
            )]
            for s in results[:8]
        ])
    )
    return ConversationHandler.END


async def cmd_search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    await update.message.reply_text(t("search_cancel", lang))
    return ConversationHandler.END


async def callback_search_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play a song chosen from search results."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    song = await get_song_by_id(song_id)
    if not song:
        await query.message.reply_text(
            t("err_not_found", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_not_found_keyboard(lang),
        )
        return

    try:
        await query.message.reply_audio(
            audio=song["file_id"],
            caption=make_audio_caption(song["title"], song["artist"]),
            reply_markup=make_song_keyboard(song["id"], lang),
        )
        await log_play(user_id, song["id"])
    except Exception as e:
        logger.error(f"Error sending search-play song {song_id}: {e}")


# ── Plain-text smart search (Feature 1: mood detection) ──────────────────────

async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text: first try mood detection, then DB, then AI fallback."""
    query_text = update.message.text.strip()
    if not query_text:
        return

    # If the home "Search" button set this flag, show inline results
    if context.user_data.pop("awaiting_search", False):
        await _show_inline_results(update, context, query_text)
        return

    user_id = update.effective_user.id
    query = query_text
    lang = await get_effective_lang(user_id)

    try:
        # Feature 1: check if text expresses a mood
        mood = await detect_mood_from_text(query)
        if mood:
            songs = await get_songs_by_mood(mood, limit=5)
            if songs:
                await update.message.reply_text(
                    t("mood_detected_text", lang, mood=mood),
                    parse_mode=ParseMode.MARKDOWN
                )
                for num, song in enumerate(songs, 1):
                    try:
                        await update.message.reply_text(f"🎵 {num}.")
                        await update.message.reply_audio(
                            audio=song["file_id"],
                            caption=make_audio_caption(song["title"], song["artist"]),
                            reply_markup=make_song_keyboard(song["id"], lang),
                        )
                        await log_play(user_id, song["id"])
                    except Exception as e:
                        logger.error(f"Error sending mood-detected song: {e}")
                return

        # Step 1: Direct DB search
        results = await search_songs(query)
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
                logger.error(f"Error sending search result audio: {e}")
            return

        # Step 2: Claude AI fallback
        await update.message.reply_text(
            t("searching", lang, query=query),
            parse_mode=ParseMode.MARKDOWN
        )

        all_songs = await get_all_songs()
        if not all_songs:
            await update.message.reply_text(
                t("err_db_empty", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_not_found_keyboard(lang),
            )
            return

        try:
            best = await find_best_match(query, all_songs)
        except Exception as e:
            logger.error(f"AI match error: {e}", exc_info=True)
            await update.message.reply_text(
                t("err_api_busy", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_not_found_keyboard(lang),
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
                logger.error(f"Error sending AI match audio: {e}")
        else:
            await update.message.reply_text(
                t("err_not_found", lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_not_found_keyboard(lang),
            )

    except Exception as e:
        logger.error(f"Unhandled error in handle_text_search: {e}", exc_info=True)
        await update.message.reply_text(
            t("err_general", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_not_found_keyboard(lang),
        )
