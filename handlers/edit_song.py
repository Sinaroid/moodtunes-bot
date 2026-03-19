import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import get_song_by_id, update_song_field, delete_song, get_effective_lang
from strings import t

logger = logging.getLogger(__name__)

# ConversationHandler states
EDIT_CHOOSING = 0
EDIT_WAITING_VALUE = 1

_FIELD_BUTTONS = {
    "en": [
        ("✏️ Title",       "title"),
        ("👤 Artist",      "artist"),
        ("🎭 Vibe",        "vibe_label"),
        ("🏷 Tags",        "mood"),
        ("⚡ Energy",      "energy"),
        ("🗑 Delete Song", "delete"),
    ],
    "fa": [
        ("✏️ عنوان",      "title"),
        ("👤 خواننده",     "artist"),
        ("🎭 ویب",        "vibe_label"),
        ("🏷 تگ‌ها",      "mood"),
        ("⚡ انرژی",      "energy"),
        ("🗑 حذف آهنگ",   "delete"),
    ],
}

_PROMPT_KEY = {
    "title":      "edit_song_prompt_title",
    "artist":     "edit_song_prompt_artist",
    "vibe_label": "edit_song_prompt_vibe",
    "mood":       "edit_song_prompt_tags",
    "energy":     "edit_song_prompt_energy",
}


def _make_edit_keyboard(song_id: int, lang: str) -> InlineKeyboardMarkup:
    buttons = _FIELD_BUTTONS.get(lang, _FIELD_BUTTONS["en"])
    rows = []
    for i in range(0, len(buttons), 2):
        row = [
            InlineKeyboardButton(label, callback_data=f"edit_field:{song_id}:{field}")
            for label, field in buttons[i:i + 2]
        ]
        rows.append(row)
    cancel = "❌ انصراف" if lang == "fa" else "❌ Cancel"
    rows.append([InlineKeyboardButton(cancel, callback_data=f"edit_field:{song_id}:cancel")])
    return InlineKeyboardMarkup(rows)


async def _show_edit_panel(message, song_id: int, lang: str):
    song = await get_song_by_id(song_id)
    if not song:
        await message.reply_text(t("edit_song_not_found", lang))
        return False
    await message.reply_text(
        t("edit_song_panel", lang, id=song_id,
          title=song["title"], artist=song["artist"]),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_make_edit_keyboard(song_id, lang),
    )
    return True


# ── Entry: /edit [id] command ─────────────────────────────────────────────────

async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.admin import is_admin
    lang = await get_effective_lang(update.effective_user.id)

    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text(t("edit_usage", lang))
        return ConversationHandler.END

    try:
        song_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t("edit_usage", lang))
        return ConversationHandler.END

    context.user_data["editing_song_id"] = song_id
    ok = await _show_edit_panel(update.message, song_id, lang)
    return EDIT_CHOOSING if ok else ConversationHandler.END


# ── Entry: ✏️ #{id} button from admin list ────────────────────────────────────

async def callback_admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.admin import is_admin
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        return ConversationHandler.END

    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return ConversationHandler.END

    lang = await get_effective_lang(query.from_user.id)
    context.user_data["editing_song_id"] = song_id
    ok = await _show_edit_panel(query.message, song_id, lang)
    return EDIT_CHOOSING if ok else ConversationHandler.END


# ── EDIT_CHOOSING state: user tapped a field button ──────────────────────────

async def callback_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.admin import is_admin
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        return ConversationHandler.END

    parts = query.data.split(":")   # edit_field:{song_id}:{field}
    try:
        song_id = int(parts[1])
        field = parts[2]
    except (IndexError, ValueError):
        return ConversationHandler.END

    lang = await get_effective_lang(query.from_user.id)

    if field == "cancel":
        await query.message.reply_text(t("edit_song_cancelled", lang))
        return ConversationHandler.END

    if field == "delete":
        song = await get_song_by_id(song_id)
        if song:
            await delete_song(song_id)
        await query.message.reply_text(t("edit_song_deleted", lang))
        return ConversationHandler.END

    context.user_data["editing_song_id"] = song_id
    context.user_data["editing_field"] = field
    await query.message.reply_text(t(_PROMPT_KEY.get(field, "edit_song_prompt_title"), lang))
    return EDIT_WAITING_VALUE


# ── EDIT_WAITING_VALUE state: user sends the new value ───────────────────────

async def edit_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.admin import is_admin
    if not is_admin(update):
        return ConversationHandler.END

    lang = await get_effective_lang(update.effective_user.id)
    song_id = context.user_data.pop("editing_song_id", None)
    field = context.user_data.pop("editing_field", None)

    if not song_id or not field:
        return ConversationHandler.END

    raw = update.message.text.strip()
    value = [tag.strip().lower() for tag in raw.split(",") if tag.strip()] \
        if field == "mood" else raw

    success = await update_song_field(song_id, field, value)
    msg = t("edit_song_updated", lang) if success else t("edit_song_not_found", lang)
    await update.message.reply_text(msg)
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    context.user_data.pop("editing_song_id", None)
    context.user_data.pop("editing_field", None)
    await update.message.reply_text(t("edit_song_cancelled", lang))
    return ConversationHandler.END
