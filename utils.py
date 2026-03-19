from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ── Mood metadata ─────────────────────────────────────────────────────────────

MOOD_EMOJIS = {
    "happy": "😊", "sad": "😢", "chill": "😌",
    "energetic": "⚡", "romantic": "💕", "nostalgic": "🌅",
    "angry": "😠", "peaceful": "🕊", "party": "🎉",
    "focus": "🎯", "workout": "💪", "melancholic": "🌙",
}

MOOD_LABELS = {
    "en": {
        "happy": "Happy", "sad": "Sad", "chill": "Chill",
        "energetic": "Energetic", "romantic": "Romantic", "nostalgic": "Nostalgic",
        "angry": "Angry", "peaceful": "Peaceful", "party": "Party",
        "focus": "Focus", "workout": "Workout", "melancholic": "Melancholic",
    },
    "fa": {
        "happy": "شاد", "sad": "غمگین", "chill": "آرام",
        "energetic": "پرانرژی", "romantic": "رمانتیک", "nostalgic": "نوستالژیک",
        "angry": "عصبانی", "peaceful": "آرامش", "party": "پارتی",
        "focus": "تمرکز", "workout": "ورزش", "melancholic": "ملانکولیک",
    },
}

VALID_MOODS = list(MOOD_EMOJIS.keys())


def _mood_label(mood: str, lang: str) -> str:
    labels = MOOD_LABELS.get(lang, MOOD_LABELS["en"])
    emoji = MOOD_EMOJIS.get(mood, "🎵")
    return f"{emoji} {labels.get(mood, mood.capitalize())}"


# ── Language selection keyboard ────────────────────────────────────────────────

def make_lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_select:fa"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_select:en"),
    ]])


# ── Home screen keyboard (mood grid) ──────────────────────────────────────────

def make_home_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    moods = VALID_MOODS  # 12 moods → 4 rows of 3
    rows = []
    for i in range(0, len(moods), 3):
        row = [
            InlineKeyboardButton(
                _mood_label(m, lang),
                callback_data=f"home_mood:{m}"
            )
            for m in moods[i:i + 3]
        ]
        rows.append(row)

    # Bottom utility row
    if lang == "fa":
        rows.append([
            InlineKeyboardButton("🎲 روزانه", callback_data="home_daily"),
            InlineKeyboardButton("📊 آمار من", callback_data="home_stats"),
            InlineKeyboardButton("🔍 جستجو", callback_data="home_search"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("🎲 Daily", callback_data="home_daily"),
            InlineKeyboardButton("📊 My Stats", callback_data="home_stats"),
            InlineKeyboardButton("🔍 Search", callback_data="home_search"),
        ])
    return InlineKeyboardMarkup(rows)


# ── Per-song action keyboard ───────────────────────────────────────────────────

def make_song_keyboard(song_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        labels = ("🎵 مشابه", "📻 رادیو", "➕ پلیست")
    else:
        labels = ("🎵 Similar", "📻 Radio", "➕ Playlist")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(labels[0], callback_data=f"similar:{song_id}"),
        InlineKeyboardButton(labels[1], callback_data=f"radio_from:{song_id}"),
        InlineKeyboardButton(labels[2], callback_data=f"add_to_playlist:{song_id}"),
    ]])


# ── "More songs" button after a mood batch ────────────────────────────────────

def make_mood_more_keyboard(mood: str, lang: str = "en") -> InlineKeyboardMarkup:
    emoji = MOOD_EMOJIS.get(mood, "🎵")
    label = _mood_label(mood, lang)
    btn_text = f"⏭ بعدی ({label})" if lang == "fa" else f"⏭ More {label}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(btn_text, callback_data=f"mood_more:{mood}"),
    ]])


# ── Radio player keyboard ──────────────────────────────────────────────────────

def make_radio_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        labels = ("⏭ بعدی", "⏹ توقف")
    else:
        labels = ("⏭ Next", "⏹ Stop")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(labels[0], callback_data="radio_next"),
        InlineKeyboardButton(labels[1], callback_data="radio_stop"),
    ]])


# ── Admin panel keyboard ───────────────────────────────────────────────────────

def make_audio_caption(title: str, artist: str) -> str:
    """Uniform caption for all audio messages."""
    return f"{title} - {artist} | @moodtunes_music_bot"


def make_admin_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        rows = [
            [
                InlineKeyboardButton("📊 آمار کامل", callback_data="admin_action:stats"),
                InlineKeyboardButton("📋 لیست آهنگ‌ها", callback_data="admin_action:list"),
            ],
            [
                InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_action:broadcast_prompt"),
                InlineKeyboardButton("✏️ ویرایش آهنگ", callback_data="admin_action:edit_prompt"),
            ],
            [
                InlineKeyboardButton("🔄 رفرش پنل", callback_data="admin_action:refresh"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("📊 Full Stats", callback_data="admin_action:stats"),
                InlineKeyboardButton("📋 Song List", callback_data="admin_action:list"),
            ],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_action:broadcast_prompt"),
                InlineKeyboardButton("✏️ Edit Song", callback_data="admin_action:edit_prompt"),
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_action:refresh"),
            ],
        ]
    return InlineKeyboardMarkup(rows)


# ── Error keyboards ────────────────────────────────────────────────────────────

def make_error_home_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    label = "🏠 خونه" if lang == "fa" else "🏠 Home"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(label, callback_data="go_home"),
    ]])


def make_not_found_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 جستجو", callback_data="home_search"),
            InlineKeyboardButton("🎲 روزانه", callback_data="home_daily"),
            InlineKeyboardButton("🏠 خونه", callback_data="go_home"),
        ]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 Search", callback_data="home_search"),
        InlineKeyboardButton("🎲 Daily", callback_data="home_daily"),
        InlineKeyboardButton("🏠 Home", callback_data="go_home"),
    ]])


def make_mood_empty_keyboard(mood: str, lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🎲 روزانه", callback_data="home_daily"),
            InlineKeyboardButton("🏠 خونه", callback_data="go_home"),
        ]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎲 Daily Mix", callback_data="home_daily"),
        InlineKeyboardButton("🏠 Home", callback_data="go_home"),
    ]])


def make_voice_error_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 جستجوی متنی", callback_data="home_search"),
            InlineKeyboardButton("🏠 خونه", callback_data="go_home"),
        ]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 Text Search", callback_data="home_search"),
        InlineKeyboardButton("🏠 Home", callback_data="go_home"),
    ]])


def make_duplicate_keyboard(song_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    if lang == "fa":
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(f"✏️ ویرایش #{song_id}", callback_data=f"admin_edit:{song_id}"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="go_home"),
        ]])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✏️ Edit #{song_id}", callback_data=f"admin_edit:{song_id}"),
        InlineKeyboardButton("🔙 Back", callback_data="go_home"),
    ]])
