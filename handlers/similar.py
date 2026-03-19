import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import get_song_by_id, get_all_songs, log_play, get_effective_lang
from strings import t
from utils import make_song_keyboard, make_audio_caption

logger = logging.getLogger(__name__)

TEMPO_ORDER = ["slow", "mid", "fast"]
DECADE_ORDER = ["60s", "70s", "80s", "90s", "2000s", "2010s", "2020s"]


def calculate_dj_similarity(seed: dict, candidate: dict) -> tuple[int, list[str], list[str]]:
    """
    Score how similar candidate is to seed using weighted DJ factors.
    Returns (score 0-100, fa_reasons, en_reasons).
    """
    score = 0
    fa_reasons: list[str] = []
    en_reasons: list[str] = []

    # Language — 25 pts
    if seed.get("language") and candidate.get("language"):
        if seed["language"] == candidate["language"]:
            score += 25
            fa_reasons.append("زبان مشترک")
            en_reasons.append("same language")

    # Shared moods — 15 pts each, max 2 moods (30 pts)
    seed_moods = set(seed.get("mood") or [])
    cand_moods = set(candidate.get("mood") or [])
    shared_moods = min(len(seed_moods & cand_moods), 2)
    if shared_moods > 0:
        score += shared_moods * 15
        fa_reasons.append("حال مشابه")
        en_reasons.append("matching vibes")

    # Energy — 15 pts
    if seed.get("energy") and candidate.get("energy"):
        if seed["energy"] == candidate["energy"]:
            score += 15
            fa_reasons.append("انرژی یکسان")
            en_reasons.append("same energy")

    # Tempo — 10 pts exact, 5 pts adjacent
    st, ct = seed.get("tempo"), candidate.get("tempo")
    if st and ct:
        if st == ct:
            score += 10
            fa_reasons.append("ریتم نزدیک")
            en_reasons.append("similar tempo")
        elif st in TEMPO_ORDER and ct in TEMPO_ORDER:
            if abs(TEMPO_ORDER.index(st) - TEMPO_ORDER.index(ct)) == 1:
                score += 5
                fa_reasons.append("ریتم نزدیک")
                en_reasons.append("similar tempo")

    # Lyrics theme — 10 pts
    if seed.get("lyrics_theme") and candidate.get("lyrics_theme"):
        if seed["lyrics_theme"] == candidate["lyrics_theme"]:
            score += 10
            fa_reasons.append("موضوع مشترک")
            en_reasons.append("shared theme")

    # Rhythm — 8 pts
    if seed.get("rhythm") and candidate.get("rhythm"):
        if seed["rhythm"] == candidate["rhythm"]:
            score += 8
            fa_reasons.append("ضرباهنگ مشابه")
            en_reasons.append("similar rhythm")

    # Vocal style — 7 pts
    if seed.get("vocal_style") and candidate.get("vocal_style"):
        if seed["vocal_style"] == candidate["vocal_style"]:
            score += 7
            fa_reasons.append("سبک صدا")
            en_reasons.append("vocal style")

    # Decade — 5 pts exact, 3 pts adjacent
    sd, cd = seed.get("decade"), candidate.get("decade")
    if sd and cd:
        if sd == cd:
            score += 5
            fa_reasons.append("دوره مشترک")
            en_reasons.append("same era")
        elif sd in DECADE_ORDER and cd in DECADE_ORDER:
            if abs(DECADE_ORDER.index(sd) - DECADE_ORDER.index(cd)) == 1:
                score += 3
                fa_reasons.append("دوره مشترک")
                en_reasons.append("same era")

    return min(score, 100), fa_reasons, en_reasons


async def callback_similar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'similar:{song_id}' callback button."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    seed = await get_song_by_id(song_id)
    if not seed:
        return

    all_songs = await get_all_songs()
    candidates = [s for s in all_songs if s["id"] != song_id]

    # Score all candidates
    scored = []
    for s in candidates:
        score, fa_r, en_r = calculate_dj_similarity(seed, s)
        scored.append((score, fa_r, en_r, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    similar = scored[:5]

    if not similar:
        await query.message.reply_text(t("similar_none", lang))
        return

    await query.message.reply_text(
        t("similar_header", lang, title=seed["title"]),
        parse_mode=ParseMode.MARKDOWN
    )

    for score, fa_reasons, en_reasons, song in similar:
        try:
            reasons = fa_reasons if lang == "fa" else en_reasons
            reasons_text = " · ".join(reasons[:3]) if reasons else ""
            pre = f"🎧 {score}% match"
            if reasons_text:
                pre += f"\n🔗 {reasons_text}"
            await query.message.reply_text(pre)
            await query.message.reply_audio(
                audio=song["file_id"],
                caption=make_audio_caption(song["title"], song["artist"]),
                reply_markup=make_song_keyboard(song["id"], lang),
            )
            await log_play(user_id, song["id"])
        except Exception as e:
            logger.error(f"Error sending similar song {song['id']}: {e}")
