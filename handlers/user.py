import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (
    get_all_songs, get_songs_by_mood, get_random_songs_varied,
    log_play, get_user_stats, set_user_language,
    get_effective_lang, is_new_user, search_songs, get_song_by_id,
)
from strings import t
from utils import (
    make_lang_keyboard, make_home_keyboard, make_song_keyboard,
    make_mood_more_keyboard, make_audio_caption, VALID_MOODS,
    make_not_found_keyboard, make_mood_empty_keyboard, make_error_home_keyboard,
)

logger = logging.getLogger(__name__)


def _daily_greeting_key() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "daily_morning"
    elif 12 <= hour < 17:
        return "daily_noon"
    elif 17 <= hour < 21:
        return "daily_evening"
    else:
        return "daily_night"


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.admin import is_admin, show_admin_panel

    if is_admin(update):
        await show_admin_panel(update, context)
        return

    user_id = update.effective_user.id

    if await is_new_user(user_id):
        await update.message.reply_text(
            "🎵 MoodTunes\n\n"
            "یه دستیار موزیک شخصیه.\n\n"
            "اسم آهنگ بفرست، ویس بده،\n"
            "یا هر چیزی بنویس —\n"
            "بهترین موزیک رو برات پیدا می‌کنم.\n\n"
            "ساخته شده برای کسایی که\n"
            "موزیک براشون فقط یه صدا نیست 🎧"
        )
        await asyncio.sleep(2)
        await update.message.reply_text(
            "زبانت رو انتخاب کن:",
            reply_markup=make_lang_keyboard(),
        )
        return

    lang = await get_effective_lang(user_id)
    await _send_home(update.message.reply_text, lang)


async def _send_home(reply_fn, lang: str, **kwargs):
    """Send the home screen (welcome + mood grid)."""
    text = (
        "🎵 *MoodTunes*\n\n"
        + (t("home_choose_mood", lang))
    )
    await reply_fn(text, parse_mode=ParseMode.MARKDOWN,
                   reply_markup=make_home_keyboard(lang), **kwargs)


# ── Language selection callback ────────────────────────────────────────────────

async def callback_lang_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":")[1]  # "en" or "fa"
    user_id = query.from_user.id
    await set_user_language(user_id, lang)

    confirmation = t("lang_set_fa", lang) if lang == "fa" else t("lang_set_en", lang)
    home_text = (
        f"{confirmation}\n\n"
        "🎵 *MoodTunes*\n\n"
        + t("home_choose_mood", lang)
    )
    await query.edit_message_text(
        home_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=make_home_keyboard(lang),
    )


# ── Home screen callbacks ──────────────────────────────────────────────────────

async def callback_home_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User tapped a mood button on the home screen."""
    query = update.callback_query
    await query.answer()

    mood = query.data.split(":")[1]
    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    await _send_mood_songs(mood, user_id, lang, query.message)


async def callback_home_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)
    await _do_daily(user_id, lang, query.message)


async def callback_home_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)
    await _do_stats(user_id, lang, query.message)


async def callback_home_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redirect to /search conversation from home button."""
    from handlers.search import cmd_search_start, SEARCH_WAITING_QUERY
    query = update.callback_query
    await query.answer()
    # Simulate a message for the conversation handler
    lang = await get_effective_lang(query.from_user.id)
    await query.message.reply_text(t("search_prompt", lang), parse_mode=ParseMode.MARKDOWN)
    # Store state so the next text message is treated as a search query
    context.user_data["awaiting_search"] = True


async def callback_mood_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⏭ More songs for a mood."""
    query = update.callback_query
    await query.answer()

    mood = query.data.split(":")[1]
    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    await _send_mood_songs(mood, user_id, lang, query.message)


# ── Shared helpers ────────────────────────────────────────────────────────────

async def _send_mood_songs(mood: str, user_id: int, lang: str, message):
    if mood not in VALID_MOODS:
        return

    try:
        songs = await get_songs_by_mood(mood, limit=5)
    except Exception as e:
        logger.error(f"DB error getting mood songs: {e}", exc_info=True)
        await message.reply_text(
            t("err_general", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_error_home_keyboard(lang),
        )
        return

    if not songs:
        await message.reply_text(
            t("err_mood_empty", lang, mood=mood),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_mood_empty_keyboard(mood, lang),
        )
        return

    await message.reply_text(
        t("mood_header", lang, mood=mood, count=len(songs)),
        parse_mode=ParseMode.MARKDOWN,
    )

    for num, song in enumerate(songs, 1):
        try:
            await message.reply_text(f"🎵 {num}.")
            await message.reply_audio(
                audio=song["file_id"],
                caption=make_audio_caption(song["title"], song["artist"]),
                reply_markup=make_song_keyboard(song["id"], lang),
            )
            await log_play(user_id, song["id"])
        except Exception as e:
            logger.error(f"Error sending mood song {song['id']}: {e}")

    # "More songs" button after the batch
    await message.reply_text(
        "—",
        reply_markup=make_mood_more_keyboard(mood, lang),
    )


async def _do_daily(user_id: int, lang: str, message):
    try:
        songs = await get_random_songs_varied(limit=3)
    except Exception as e:
        logger.error(f"DB error in _do_daily: {e}", exc_info=True)
        await message.reply_text(
            t("err_general", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_error_home_keyboard(lang),
        )
        return

    if not songs:
        await message.reply_text(
            t("err_db_empty", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_error_home_keyboard(lang),
        )
        return

    greeting_key = _daily_greeting_key()
    await message.reply_text(t(greeting_key, lang), parse_mode=ParseMode.MARKDOWN)

    for num, song in enumerate(songs, 1):
        try:
            await message.reply_text(f"🌅 {num}.")
            await message.reply_audio(
                audio=song["file_id"],
                caption=make_audio_caption(song["title"], song["artist"]),
                reply_markup=make_song_keyboard(song["id"], lang),
            )
            await log_play(user_id, song["id"])
        except Exception as e:
            logger.error(f"Error sending daily song {song['id']}: {e}")


async def _do_stats(user_id: int, lang: str, message):
    from database import get_user_stats
    stats = await get_user_stats(user_id)
    if stats["total_plays"] == 0:
        await message.reply_text(t("stats_empty", lang), parse_mode=ParseMode.MARKDOWN)
        return
    top_text = ""
    for i, s in enumerate(stats["top_songs"], 1):
        top_text += t("stats_song_line", lang,
                      i=i, title=s["title"], artist=s["artist"], plays=s["plays"])
    await message.reply_text(
        t("stats_header", lang, total=stats["total_plays"], mood=stats["favorite_mood"])
        + (top_text or t("stats_no_top", lang)),
        parse_mode=ParseMode.MARKDOWN,
    )


# ── Traditional command handlers (still supported) ────────────────────────────

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        t("language_select", "en"),
        reply_markup=make_lang_keyboard(),
    )


async def cmd_lang_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await set_user_language(user_id, "en")
    await update.message.reply_text(t("lang_set_en", "en"))
    await _send_home(update.message.reply_text, "en")


async def cmd_lang_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await set_user_language(user_id, "fa")
    await update.message.reply_text(t("lang_set_fa", "fa"))
    await _send_home(update.message.reply_text, "fa")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    songs = await get_all_songs()
    if not songs:
        await update.message.reply_text(t("list_empty", lang))
        return

    groups: dict[str, list] = {}
    for song in songs:
        primary = song["mood"][0] if song["mood"] else "other"
        groups.setdefault(primary, []).append(song)

    lines = [t("list_header", lang)]
    for mood in VALID_MOODS:
        if mood in groups:
            lines.append(t("list_group_header", lang, mood=mood, count=len(groups[mood])))
            for s in groups[mood]:
                dur = f"{s['duration'] // 60}:{s['duration'] % 60:02d}" if s["duration"] else "?"
                lines.append(t("list_song_line", lang,
                               id=s["id"], title=s["title"], artist=s["artist"], dur=dur))
            lines.append("")

    if "other" in groups:
        lines.append(t("list_group_header", lang, mood="other", count=len(groups["other"])))
        for s in groups["other"]:
            dur = f"{s['duration'] // 60}:{s['duration'] % 60:02d}" if s["duration"] else "?"
            lines.append(t("list_song_line", lang,
                           id=s["id"], title=s["title"], artist=s["artist"], dur=dur))

    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000], parse_mode=ParseMode.MARKDOWN)


async def cmd_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text(
            t("mood_usage", lang, list=" | ".join(VALID_MOODS)),
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    mood = context.args[0].lower().strip()
    if mood not in VALID_MOODS:
        await update.message.reply_text(
            t("mood_invalid", lang, mood=mood, list=", ".join(VALID_MOODS)),
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    await _send_mood_songs(mood, update.effective_user.id, lang, update.message)


async def cmd_radio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.radio_mode import start_radio_from_seed
    lang = await get_effective_lang(update.effective_user.id)
    if not context.args:
        await update.message.reply_text(t("radio_usage", lang), parse_mode=ParseMode.MARKDOWN)
        return
    query = " ".join(context.args)
    matches = await search_songs(query)
    if not matches:
        await update.message.reply_text(
            t("radio_not_found", lang, query=query), parse_mode=ParseMode.MARKDOWN
        )
        return
    await start_radio_from_seed(matches[0], update, context)


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)
    await _do_daily(user_id, lang, update.message)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)
    await _do_stats(user_id, lang, update.message)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed metadata + top similar songs for a song ID."""
    from handlers.similar import calculate_dj_similarity

    lang = await get_effective_lang(update.effective_user.id)

    if not context.args:
        usage = "استفاده: `/info [شناسه]`" if lang == "fa" else "Usage: `/info [id]`"
        await update.message.reply_text(usage, parse_mode=ParseMode.MARKDOWN)
        return

    try:
        song_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عدد باشه." if lang == "fa" else "❌ ID must be a number.")
        return

    song = await get_song_by_id(song_id)
    if not song:
        await update.message.reply_text(f"❌ آهنگ #{song_id} پیدا نشد." if lang == "fa" else f"❌ Song #{song_id} not found.")
        return

    moods_str = " ".join(f"#{m}" for m in song.get("mood") or []) or "—"
    fields = [
        f"🎵 *{song['title']}* — {song['artist']}",
        f"🆔 #{song['id']}",
        f"🎭 {song.get('vibe_label') or '—'}",
        f"⚡ {song.get('energy') or '—'}",
        f"🏷 {moods_str}",
        f"🌐 {song.get('language') or '—'}",
        f"🥁 tempo: {song.get('tempo') or '—'}  rhythm: {song.get('rhythm') or '—'}",
        f"🎤 {song.get('vocal_style') or '—'}",
        f"📖 {song.get('lyrics_theme') or '—'}",
        f"📅 {song.get('decade') or '—'}",
        f"▶️ {song.get('play_count') or 0} plays",
    ]
    await update.message.reply_text("\n".join(fields), parse_mode=ParseMode.MARKDOWN)

    # Top 3 similar songs
    all_songs = await get_all_songs()
    candidates = [s for s in all_songs if s["id"] != song_id]
    if candidates:
        scored = sorted(
            candidates,
            key=lambda s: calculate_dj_similarity(song, s)[0],
            reverse=True
        )[:3]
        header = "🔗 *مشابه‌ترین آهنگ‌ها:*" if lang == "fa" else "🔗 *Top similar songs:*"
        lines = [header]
        for s in scored:
            score, _, _ = calculate_dj_similarity(song, s)
            lines.append(f"  {score}% — *{s['title']}* — {s['artist']}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
