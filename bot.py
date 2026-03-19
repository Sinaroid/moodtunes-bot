import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
def setup_logging():
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = RotatingFileHandler("errors.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

setup_logging()
logger = logging.getLogger(__name__)

# ── Import handlers (after logging is configured) ─────────────────────────────
from database import init_db
from handlers.admin import (
    handle_audio, cmd_delete, cmd_stats_admin, cmd_list_admin, cmd_broadcast,
    cmd_reanalyze, callback_admin_action,
)
from handlers.user import (
    cmd_start, cmd_list, cmd_mood, cmd_radio, cmd_daily, cmd_stats, cmd_info,
    cmd_language, cmd_lang_en, cmd_lang_fa,
    callback_lang_select,
    callback_home_mood, callback_home_daily, callback_home_stats,
    callback_home_search, callback_mood_more, _send_home,
)
from handlers.search import (
    handle_text_search,
    cmd_search_start, cmd_search_query, cmd_search_cancel,
    callback_search_play,
    SEARCH_WAITING_QUERY,
)
from handlers.voice import handle_voice_message
from handlers.similar import callback_similar
from handlers.radio_mode import callback_radio_next, callback_radio_stop, callback_radio_from
from handlers.playlists import (
    cmd_my_playlists,
    callback_add_to_playlist,
    callback_playlist_add_confirm,
    callback_playlist_view,
    callback_playlist_create_new,
    playlist_name_received,
    playlist_cancel,
    PLAYLIST_WAITING_NAME,
)
from handlers.edit_song import (
    cmd_edit,
    callback_admin_edit,
    callback_edit_field,
    edit_value_received,
    edit_cancel,
    EDIT_CHOOSING,
    EDIT_WAITING_VALUE,
)


# ── go_home callback ──────────────────────────────────────────────────────────
async def callback_go_home(update: object, context: ContextTypes.DEFAULT_TYPE):
    from telegram import Update as TGUpdate
    if not isinstance(update, TGUpdate):
        return
    query = update.callback_query
    if not query:
        return
    await query.answer()
    from database import get_effective_lang
    lang = await get_effective_lang(query.from_user.id)
    await _send_home(query.message.reply_text, lang)


# ── Global error handler ──────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again."
            )
        except Exception:
            pass


# ── Bot setup ─────────────────────────────────────────────────────────────────
async def post_init(application: Application):
    await init_db()
    logger.info("MoodTunes bot started and DB initialized.")


def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN is not set in .env")
        sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY is not set in .env")
        sys.exit(1)

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # ── ConversationHandlers (BEFORE general message handler) ────────────────

    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", cmd_search_start)],
        states={
            SEARCH_WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_search_query),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_search_cancel)],
        per_chat=True,
    )

    create_playlist_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(callback_playlist_create_new, pattern=r"^playlist_create_new:\d+$"),
        ],
        states={
            PLAYLIST_WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, playlist_name_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", playlist_cancel)],
        per_chat=True,
        per_message=False,
    )

    edit_song_conv = ConversationHandler(
        entry_points=[
            CommandHandler("edit", cmd_edit),
            CallbackQueryHandler(callback_admin_edit, pattern=r"^admin_edit:\d+$"),
        ],
        states={
            EDIT_CHOOSING: [
                CallbackQueryHandler(callback_edit_field, pattern=r"^edit_field:\d+:\w+$"),
            ],
            EDIT_WAITING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", edit_cancel)],
        per_chat=True,
        per_message=False,
    )

    app.add_handler(search_conv)
    app.add_handler(create_playlist_conv)
    app.add_handler(edit_song_conv)

    # ── User commands ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("list",       cmd_list))
    app.add_handler(CommandHandler("mood",       cmd_mood))
    app.add_handler(CommandHandler("radio",      cmd_radio))
    app.add_handler(CommandHandler("daily",      cmd_daily))
    app.add_handler(CommandHandler("stats",      cmd_stats))
    app.add_handler(CommandHandler("myplaylists", cmd_my_playlists))

    # Language commands
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("lang_en",  cmd_lang_en))
    app.add_handler(CommandHandler("lang_fa",  cmd_lang_fa))

    # ── Admin commands ────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("delete",      cmd_delete))
    app.add_handler(CommandHandler("stats_admin", cmd_stats_admin))
    app.add_handler(CommandHandler("list_admin",  cmd_list_admin))
    app.add_handler(CommandHandler("broadcast",   cmd_broadcast))
    app.add_handler(CommandHandler("reanalyze",   cmd_reanalyze))
    app.add_handler(CommandHandler("info",        cmd_info))
    # /edit is handled by edit_song_conv (registered above)

    # ── Callback query handlers ───────────────────────────────────────────────

    # go_home (error recovery button)
    app.add_handler(CallbackQueryHandler(callback_go_home, pattern=r"^go_home$"))

    # Language & home screen
    app.add_handler(CallbackQueryHandler(callback_lang_select,  pattern=r"^lang_select:(en|fa)$"))
    app.add_handler(CallbackQueryHandler(callback_home_mood,    pattern=r"^home_mood:\w+$"))
    app.add_handler(CallbackQueryHandler(callback_home_daily,   pattern=r"^home_daily$"))
    app.add_handler(CallbackQueryHandler(callback_home_stats,   pattern=r"^home_stats$"))
    app.add_handler(CallbackQueryHandler(callback_home_search,  pattern=r"^home_search$"))
    app.add_handler(CallbackQueryHandler(callback_mood_more,    pattern=r"^mood_more:\w+$"))

    # Song actions
    app.add_handler(CallbackQueryHandler(callback_similar,    pattern=r"^similar:\d+$"))
    app.add_handler(CallbackQueryHandler(callback_radio_from, pattern=r"^radio_from:\d+$"))
    app.add_handler(CallbackQueryHandler(callback_radio_next, pattern=r"^radio_next$"))
    app.add_handler(CallbackQueryHandler(callback_radio_stop, pattern=r"^radio_stop$"))

    # Playlists
    app.add_handler(CallbackQueryHandler(callback_add_to_playlist,      pattern=r"^add_to_playlist:\d+$"))
    app.add_handler(CallbackQueryHandler(callback_playlist_add_confirm, pattern=r"^playlist_add_confirm:\d+:\d+$"))
    app.add_handler(CallbackQueryHandler(callback_playlist_view,        pattern=r"^playlist_view:\d+$"))

    # Search results
    app.add_handler(CallbackQueryHandler(callback_search_play, pattern=r"^search_play:\d+$"))

    # Admin panel
    app.add_handler(CallbackQueryHandler(callback_admin_action, pattern=r"^admin_action:\w+$"))

    # ── Message handlers ──────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_search))

    # ── Error handler ─────────────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    logger.info("MoodTunes is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
