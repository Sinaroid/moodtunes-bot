import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (
    get_song_by_id, get_all_songs, log_play, get_effective_lang,
    set_radio_queue, get_radio_queue, advance_radio_queue, clear_radio_queue,
)
from strings import t
from utils import make_radio_keyboard, make_audio_caption
from handlers.similar import calculate_dj_similarity

logger = logging.getLogger(__name__)


def _build_dj_queue(seed: dict, all_songs: list[dict], max_length: int = 10) -> list[dict]:
    """
    Build a greedy DJ queue starting from seed.
    Each next song = highest similarity to the CURRENT song.
    No repeats, no consecutive same artist.
    """
    used_ids = {seed["id"]}
    queue: list[dict] = []
    current = seed

    while len(queue) < max_length:
        candidates = [s for s in all_songs if s["id"] not in used_ids]
        if not candidates:
            break

        # Exclude consecutive same artist
        last_artist = (queue[-1]["artist"] if queue else seed["artist"]).lower()
        non_same_artist = [s for s in candidates if s["artist"].lower() != last_artist]
        pool = non_same_artist if non_same_artist else candidates

        # Pick highest similarity to current
        best = max(pool, key=lambda s: calculate_dj_similarity(current, s)[0])
        queue.append(best)
        used_ids.add(best["id"])
        current = best

    return queue


async def start_radio_from_seed(seed: dict, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Build a DJ radio queue from a seed song and send the first track."""
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)

    all_songs = await get_all_songs()
    candidates = [s for s in all_songs if s["id"] != seed["id"]]

    if not candidates:
        await update.effective_message.reply_text(t("radio_no_similar", lang, title=seed["title"]))
        return

    queue = _build_dj_queue(seed, all_songs)

    if not queue:
        await update.effective_message.reply_text(t("radio_no_similar", lang, title=seed["title"]))
        return

    song_ids = [s["id"] for s in queue]
    await set_radio_queue(user_id, song_ids, position=0)

    first = queue[0]
    await _send_radio_song(first, 1, len(song_ids), update.effective_message, user_id, lang)


async def callback_radio_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ⏭ Next button."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    next_id = await advance_radio_queue(user_id)
    if next_id is None:
        await query.message.reply_text(t("radio_ended", lang), parse_mode=ParseMode.MARKDOWN)
        return

    queue = await get_radio_queue(user_id)
    song = await get_song_by_id(next_id)
    if not song:
        await query.message.reply_text(t("radio_ended", lang))
        return

    pos = queue["position"] + 1
    total = len(queue["song_ids"])
    await _send_radio_song(song, pos, total, query.message, user_id, lang)


async def callback_radio_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ⏹ Stop button."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    await clear_radio_queue(user_id)
    await query.message.reply_text(t("radio_stopped", lang), parse_mode=ParseMode.MARKDOWN)


async def callback_radio_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'radio_from:{song_id}' — start radio from a song's inline button."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    from database import get_song_by_id
    seed = await get_song_by_id(song_id)
    if not seed:
        return

    # Fake an update-like object so start_radio_from_seed can use effective_message
    class _FakeUpdate:
        effective_user = query.from_user
        effective_message = query.message
    await start_radio_from_seed(seed, _FakeUpdate(), context)


async def _send_radio_song(song: dict, pos: int, total: int, message, user_id: int, lang: str):
    """Send a single song with radio position info and next/stop buttons."""
    try:
        await message.reply_text(
            t("radio_now_playing", lang, pos=pos, total=total),
            parse_mode=ParseMode.MARKDOWN,
        )
        await message.reply_audio(
            audio=song["file_id"],
            caption=make_audio_caption(song["title"], song["artist"]),
            reply_markup=make_radio_keyboard(lang),
        )
        await log_play(user_id, song["id"])
    except Exception as e:
        logger.error(f"Error sending radio song {song['id']}: {e}")
