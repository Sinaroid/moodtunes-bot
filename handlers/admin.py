import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    add_song, delete_song, get_admin_stats, get_song_by_id,
    get_all_user_ids, get_all_songs, get_effective_lang,
    DuplicateSongError, update_song_extended_fields, get_songs_needing_reanalysis,
)
from ai_analyzer import analyze_song_vibe
from strings import t
from utils import make_admin_keyboard, make_song_keyboard, make_audio_caption, make_duplicate_keyboard

logger = logging.getLogger(__name__)


def get_admin_id() -> str:
    raw = os.getenv("ADMIN_ID", "")
    return raw.lstrip("@").lower()


def is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    admin_id = get_admin_id()
    if user.username and user.username.lower() == admin_id:
        return True
    return False


def _format_admin_panel(stats: dict, lang: str) -> str:
    top_song = stats.get("top_song") or ("—" if lang == "en" else "—")
    top_mood = stats.get("top_mood_today") or ("—" if lang == "en" else "—")
    updated_at = datetime.now().strftime("%H:%M:%S")
    return t(
        "admin_panel", lang,
        users=stats["total_users"],
        new_today=stats.get("new_users_today", 0),
        new_week=stats.get("new_users_week", 0),
        songs=stats["total_songs"],
        today_plays=stats.get("today_plays", 0),
        week_plays=stats.get("plays_week", 0),
        total_plays=stats["total_plays"],
        top_song=top_song,
        top_mood=top_mood,
        updated_at=updated_at,
    )


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin control panel with inline buttons on /start."""
    stats = await get_admin_stats()
    lang = await get_effective_lang(update.effective_user.id)
    await update.message.reply_text(
        _format_admin_panel(stats, lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=make_admin_keyboard(lang),
    )


# ── Admin action callbacks (triggered by admin panel buttons) ─────────────────

async def callback_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        return

    action = query.data.split(":")[1]
    lang = await get_effective_lang(query.from_user.id)

    if action == "list":
        await _do_list_admin(query.message, lang)

    elif action == "stats":
        await _do_stats_admin(query.message, lang)

    elif action == "broadcast_prompt":
        await query.message.reply_text(
            "📢 Send: `/broadcast [message]`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif action == "edit_prompt":
        msg = "✏️ استفاده: `/edit [شناسه]`" if lang == "fa" else "✏️ Usage: `/edit [id]`"
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif action == "refresh":
        try:
            stats = await get_admin_stats()
            await query.edit_message_text(
                _format_admin_panel(stats, lang),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=make_admin_keyboard(lang),
            )
        except Exception:
            pass  # message unchanged is fine


async def _do_stats_admin(message, lang: str):
    try:
        stats = await get_admin_stats()

        # Top 5 songs
        top5_lines = ""
        for i, s in enumerate(stats.get("top_songs", [])[:5], 1):
            top5_lines += f"  {i}. *{s['title']}* — {s['artist']} ({s['plays']} plays)\n"
        top5_lines = top5_lines or "  —"

        # Mood counts
        mood_counts = ""
        for mood, cnt in stats.get("mood_counts", {}).items():
            mood_counts += f"#{mood}: {cnt}  "
        mood_counts = mood_counts.strip() or "—"

        last_song = stats.get("last_song") or "—"

        await message.reply_text(
            t("admin_stats_full", lang,
              users=stats["total_users"],
              new_today=stats.get("new_users_today", 0),
              new_week=stats.get("new_users_week", 0),
              lang_fa=stats.get("lang_fa", 0),
              lang_en=stats.get("lang_en", 0),
              songs=stats["total_songs"],
              mood_counts=mood_counts,
              today_plays=stats.get("today_plays", 0),
              week_plays=stats.get("plays_week", 0),
              month_plays=stats.get("plays_month", 0),
              total_plays=stats["total_plays"],
              top5=top5_lines,
              last_song=last_song,
              size=stats.get("db_size_kb", 0)),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Error in _do_stats_admin: {e}", exc_info=True)
        await message.reply_text("❌ Could not load stats." if lang == "en" else "❌ آمار لود نشد.")


async def _do_list_admin(message, lang: str):
    songs = await get_all_songs()
    if not songs:
        await message.reply_text(t("admin_list_empty", lang))
        return

    await message.reply_text(
        t("admin_list_header", lang) + f"({len(songs)} songs total)",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Send batches of 10 songs with edit buttons
    batch_size = 10
    for batch_start in range(0, len(songs), batch_size):
        batch = songs[batch_start:batch_start + batch_size]

        lines = []
        for song in batch:
            plays = song.get("play_count") or 0
            lines.append(f"#{song['id']} | 🎵 {song['title']} — {song['artist']} | ▶{plays}")
        text = "\n".join(lines)

        # Edit buttons: 3 per row
        btn_rows = []
        row = []
        for song in batch:
            row.append(InlineKeyboardButton(
                f"✏️ #{song['id']}",
                callback_data=f"admin_edit:{song['id']}"
            ))
            if len(row) == 3:
                btn_rows.append(row)
                row = []
        if row:
            btn_rows.append(row)

        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(btn_rows),
        )


# ── Audio upload handler ───────────────────────────────────────────────────────

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sends MP3 → analyze vibe → save to DB."""
    if not is_admin(update):
        return

    audio = update.message.audio
    if not audio:
        return

    lang = await get_effective_lang(update.effective_user.id)
    file_id = audio.file_id
    title = audio.title or "Unknown Title"
    artist = audio.performer or "Unknown Artist"
    duration = audio.duration or 0

    status_msg = await update.message.reply_text(
        t("admin_analyzing", lang, title=title, artist=artist),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        vibe = await analyze_song_vibe(title, artist)
        added_by = update.effective_user.username or str(update.effective_user.id)
        song_id = await add_song(
            title=title, artist=artist, file_id=file_id, duration=duration,
            mood=vibe["mood"], vibe_label=vibe["vibe_label"], energy=vibe["energy"],
            added_by=added_by,
            language=vibe.get("language"), tempo=vibe.get("tempo"),
            rhythm=vibe.get("rhythm"), lyrics_theme=vibe.get("lyrics_theme"),
            vocal_style=vibe.get("vocal_style"), decade=vibe.get("decade"),
        )
        mood_tags = ", ".join(f"#{m}" for m in vibe["mood"])
        await status_msg.edit_text(
            t("admin_song_added", lang,
              id=song_id, title=title, artist=artist,
              vibe=vibe["vibe_label"], energy=vibe["energy"], moods=mood_tags),
            parse_mode=ParseMode.MARKDOWN
        )
    except DuplicateSongError as e:
        await status_msg.edit_text(
            t("admin_duplicate_song", lang,
              title=e.title, artist=e.artist, id=e.song_id),
            reply_markup=make_duplicate_keyboard(e.song_id, lang),
        )
    except Exception as e:
        logger.error(f"Error adding song: {e}", exc_info=True)
        await status_msg.edit_text(
            t("err_upload_failed", lang, error=str(e)),
            parse_mode=ParseMode.MARKDOWN,
        )


# ── Admin commands ─────────────────────────────────────────────────────────────

async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return
    if not context.args:
        await update.message.reply_text(t("admin_delete_usage", lang), parse_mode=ParseMode.MARKDOWN)
        return
    try:
        song_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t("admin_delete_invalid", lang), parse_mode=ParseMode.MARKDOWN)
        return
    song = await get_song_by_id(song_id)
    if not song:
        await update.message.reply_text(t("admin_delete_not_found", lang, id=song_id))
        return
    success = await delete_song(song_id)
    if success:
        await update.message.reply_text(
            t("admin_delete_success", lang, title=song["title"], artist=song["artist"]),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(t("admin_delete_failed", lang))


async def cmd_stats_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return
    await _do_stats_admin(update.message, lang)


async def cmd_list_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return
    await _do_list_admin(update.message, lang)


async def cmd_reanalyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Re-analyze songs missing extended DJ metadata."""
    lang = await get_effective_lang(update.effective_user.id)
    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return

    songs = await get_songs_needing_reanalysis()
    if not songs:
        msg = "✅ همه آهنگ‌ها قبلاً آنالیز شدن." if lang == "fa" else "✅ All songs already analyzed."
        await update.message.reply_text(msg)
        return

    status_msg = await update.message.reply_text(
        f"🔄 شروع آنالیز {len(songs)} آهنگ..." if lang == "fa"
        else f"🔄 Analyzing {len(songs)} songs..."
    )

    done = 0
    failed = 0
    for i, song in enumerate(songs, 1):
        try:
            vibe = await analyze_song_vibe(song["title"], song["artist"])
            await update_song_extended_fields(song["id"], {
                "language": vibe.get("language"),
                "tempo": vibe.get("tempo"),
                "rhythm": vibe.get("rhythm"),
                "lyrics_theme": vibe.get("lyrics_theme"),
                "vocal_style": vibe.get("vocal_style"),
                "decade": vibe.get("decade"),
            })
            done += 1
        except Exception as e:
            logger.error(f"Reanalyze failed for song #{song['id']}: {e}")
            failed += 1

        if i % 5 == 0 or i == len(songs):
            try:
                progress = f"آپدیت: {i}/{len(songs)} آهنگ..." if lang == "fa" \
                    else f"Progress: {i}/{len(songs)} songs..."
                await status_msg.edit_text(progress)
            except Exception:
                pass

    summary = (
        f"✅ {done} آهنگ آنالیز شد" + (f" | ❌ {failed} خطا" if failed else "")
        if lang == "fa"
        else f"✅ {done} songs analyzed" + (f" | ❌ {failed} failed" if failed else "")
    )
    await status_msg.edit_text(summary)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = await get_effective_lang(update.effective_user.id)
    if not is_admin(update):
        await update.message.reply_text(t("admin_only", lang))
        return
    if not context.args:
        await update.message.reply_text(t("broadcast_usage", lang), parse_mode=ParseMode.MARKDOWN)
        return
    message_text = " ".join(context.args)
    user_ids = await get_all_user_ids()
    if not user_ids:
        await update.message.reply_text(t("broadcast_no_users", lang))
        return
    status_msg = await update.message.reply_text(
        t("broadcast_sending", lang, count=len(user_ids))
    )
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {message_text}")
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for user {uid}: {e}")
            failed += 1
    await status_msg.edit_text(t("broadcast_done", lang, sent=sent, failed=failed))
