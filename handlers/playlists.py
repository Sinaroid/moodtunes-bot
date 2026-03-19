import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (
    get_effective_lang, get_user_playlists, create_playlist,
    get_playlist_by_id, add_song_to_playlist, get_playlist_songs,
    get_song_by_id,
)
from strings import t
from utils import make_song_keyboard

logger = logging.getLogger(__name__)

# ConversationHandler states
PLAYLIST_WAITING_NAME = 0


# ── /myplaylists command ───────────────────────────────────────────────────────

async def cmd_my_playlists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all user playlists."""
    user_id = update.effective_user.id
    lang = await get_effective_lang(user_id)
    playlists = await get_user_playlists(user_id)

    if not playlists:
        await update.message.reply_text(
            t("playlist_list_empty", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    lines = [t("playlist_list_header", lang)]
    buttons = []
    for pl in playlists:
        songs = await get_playlist_songs(pl["id"])
        lines.append(t("playlist_item", lang, name=pl["name"], count=len(songs)))
        buttons.append([InlineKeyboardButton(
            f"📁 {pl['name']} ({len(songs)})",
            callback_data=f"playlist_view:{pl['id']}"
        )])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ── Add-to-playlist callback ──────────────────────────────────────────────────

async def callback_add_to_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show playlist picker when user taps ➕ Playlist on a song."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    playlists = await get_user_playlists(user_id)

    buttons = []
    for pl in playlists:
        buttons.append([InlineKeyboardButton(
            f"📁 {pl['name']}",
            callback_data=f"playlist_add_confirm:{pl['id']}:{song_id}"
        )])
    buttons.append([InlineKeyboardButton(
        t("playlist_create_new_btn", lang),
        callback_data=f"playlist_create_new:{song_id}"
    )])

    await query.message.reply_text(
        t("playlist_add_to_which", lang),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def callback_playlist_add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add song to an existing playlist."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        parts = query.data.split(":")
        playlist_id = int(parts[1])
        song_id = int(parts[2])
    except (IndexError, ValueError):
        return

    playlist = await get_playlist_by_id(playlist_id)
    if not playlist or playlist["user_id"] != user_id:
        await query.message.reply_text(t("playlist_not_found", lang))
        return

    await add_song_to_playlist(playlist_id, song_id)
    await query.message.reply_text(
        t("playlist_added", lang, name=playlist["name"]),
        parse_mode=ParseMode.MARKDOWN
    )


# ── Playlist view callback ─────────────────────────────────────────────────────

async def callback_playlist_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show songs in a playlist."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        playlist_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return

    playlist = await get_playlist_by_id(playlist_id)
    if not playlist or playlist["user_id"] != user_id:
        await query.message.reply_text(t("playlist_not_found", lang))
        return

    songs = await get_playlist_songs(playlist_id)
    header = t("playlist_view_header", lang, name=playlist["name"])

    if not songs:
        await query.message.reply_text(
            header + t("playlist_view_empty", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    lines = [header]
    for s in songs:
        lines.append(t("playlist_view_song", lang, title=s["title"], artist=s["artist"]))
    await query.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ── Create-new-playlist ConversationHandler ────────────────────────────────────

async def callback_playlist_create_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: user wants to create a new playlist for a song."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await get_effective_lang(user_id)

    try:
        song_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return ConversationHandler.END

    context.user_data["pending_playlist_song_id"] = song_id
    context.user_data["pending_playlist_lang"] = lang

    await query.message.reply_text(
        t("playlist_name_prompt", lang),
        parse_mode=ParseMode.MARKDOWN
    )
    return PLAYLIST_WAITING_NAME


async def playlist_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive playlist name, create it, add the pending song."""
    user_id = update.effective_user.id
    lang = context.user_data.get("pending_playlist_lang", "en")
    song_id = context.user_data.get("pending_playlist_song_id")
    name = update.message.text.strip()[:100]

    playlist_id = await create_playlist(user_id, name)
    if song_id:
        await add_song_to_playlist(playlist_id, song_id)

    await update.message.reply_text(
        t("playlist_created", lang, name=name),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.pop("pending_playlist_song_id", None)
    context.user_data.pop("pending_playlist_lang", None)
    return ConversationHandler.END


async def playlist_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    await update.message.reply_text(t("playlist_cancel", lang))
    return ConversationHandler.END
