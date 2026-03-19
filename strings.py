"""
Bilingual string table for MoodTunes bot.
Usage: from strings import t
       t("welcome", lang)
       t("mood_header", lang, mood="happy", count=3)
"""

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ── Language selection ────────────────────────────────────────────────
        "language_select": (
            "🌍 Please choose your language:\n\n"
            "🇮🇷 فارسی - /lang_fa\n"
            "🇬🇧 English - /lang_en"
        ),
        "lang_set_en": "🇬🇧 Language set to English!",
        "lang_set_fa": "🇮🇷 زبان به فارسی تغییر کرد!",

        # ── Welcome ───────────────────────────────────────────────────────────
        "welcome": (
            "🎵 *Welcome to MoodTunes!*\n\n"
            "I match music to your mood using AI. Here's what I can do:\n\n"
            "🎭 `/mood [mood]` — Get 3-5 songs for a mood\n"
            "📻 `/radio [song]` — 5 similar songs by vibe\n"
            "📋 `/list` — All songs grouped by mood\n"
            "🎲 `/daily` — 3 random songs from different moods\n"
            "📊 `/stats` — Your listening stats\n"
            "🌍 `/language` — Change language\n\n"
            "💬 *Or just type anything* — I'll search for a matching song!\n\n"
            "🎵 *Available moods:* `happy` `sad` `chill` `energetic` `romantic` "
            "`nostalgic` `angry` `peaceful` `party` `focus` `workout` `melancholic`"
        ),

        # ── Search ────────────────────────────────────────────────────────────
        "searching": "🔍 Searching for *{query}*...",
        "found_db": "🔍 Found: *{title}*\n👤 {artist}\n🎭 _{vibe}_\n🏷 {moods}",
        "found_ai": "🤖 AI Match: *{title}*\n👤 {artist}\n🎭 _{vibe}_\n🏷 {moods}",
        "not_found": (
            "😔 No match found for *{query}*.\n\n"
            "Try:\n• /list — see all songs\n"
            "• /mood [mood] — browse by mood\n"
            "• /daily — random picks"
        ),

        # ── Mood ──────────────────────────────────────────────────────────────
        "mood_usage": "Usage: /mood [mood]\n\nAvailable moods:\n{list}",
        "mood_invalid": "❌ Unknown mood `{mood}`.\n\nAvailable: {list}",
        "mood_header": "🎭 Mood: #{mood} — {count} song(s) incoming!",
        "mood_empty": "😔 No songs found for mood `{mood}` yet.",
        "mood_song_caption": "🎵 *{title}*\n👤 {artist}\n🎭 _{vibe}_",

        # ── Radio ─────────────────────────────────────────────────────────────
        "radio_usage": "Usage: /radio [song name or artist]",
        "radio_not_found": "❌ Couldn't find a song matching `{query}` in the library.",
        "radio_header": (
            "📻 *Radio based on:* {title} — {artist}\n"
            "🎭 Vibe: _{vibe}_\n\n"
            "Sending {count} similar songs..."
        ),
        "radio_no_similar": "😔 Found *{title}* but no similar songs yet.",
        "radio_song_caption": "🎵 *{title}*\n👤 {artist}\n⚡ Energy: {energy}",

        # ── Daily ─────────────────────────────────────────────────────────────
        "daily_header": "🎲 *Daily Mix* — 3 songs from different vibes!",
        "daily_empty": "😔 Library is empty. Check back later!",
        "daily_song_caption": "🎵 *{title}*\n👤 {artist}\n🏷 {moods}",

        # ── List ──────────────────────────────────────────────────────────────
        "list_empty": "😔 No songs in the library yet. Stay tuned!",
        "list_header": "🎵 *Song Library*\n",
        "list_group_header": "*#{mood}* ({count} songs)",
        "list_song_line": "  `{id}`. {title} — {artist} [{dur}]",

        # ── Stats ─────────────────────────────────────────────────────────────
        "stats_empty": (
            "📊 *Your Stats*\n\n"
            "You haven't played any songs yet.\n"
            "Try /daily or /mood to get started!"
        ),
        "stats_header": (
            "📊 *Your Listening Stats*\n\n"
            "▶️ Total Plays: *{total}*\n"
            "💖 Favorite Mood: *#{mood}*\n\n"
            "🏆 *Top Songs:*\n"
        ),
        "stats_no_top": "  None yet.",
        "stats_song_line": "  {i}. *{title}* — {artist} ({plays}x)\n",

        # ── Admin ─────────────────────────────────────────────────────────────
        "admin_only": "⛔ Admin only.",
        "admin_panel": (
            "👑 *MoodTunes Admin Panel*\n\n"
            "Admin commands:\n"
            "📤 Send MP3 → Add to database\n"
            "/delete [id] → Remove song\n"
            "/stats_admin → Full stats\n"
            "/list_admin → Full list with IDs\n"
            "/broadcast [message] → Send to all users\n\n"
            "👥 Users: *{users}*\n"
            "🎵 Songs: *{songs}*"
        ),
        "admin_song_added": (
            "✅ *Song added!* (ID: `{id}`)\n\n"
            "🎵 *{title}* — {artist}\n"
            "🎭 Vibe: _{vibe}_\n"
            "⚡ Energy: *{energy}*\n"
            "🏷 Moods: {moods}"
        ),
        "admin_analyzing": "🎵 Analyzing *{title}* by *{artist}*...",
        "admin_song_failed": "❌ Failed to add song: {error}",
        "admin_delete_usage": "Usage: /delete [song_id]",
        "admin_delete_invalid": "❌ Invalid ID. Usage: /delete [song_id]",
        "admin_delete_not_found": "❌ Song with ID {id} not found.",
        "admin_delete_success": "✅ Deleted: *{title}* by {artist}",
        "admin_delete_failed": "❌ Failed to delete song.",
        "admin_stats": (
            "📊 *Full Stats*\n\n"
            "👥 Users: *{users}*\n"
            "🎵 Total Songs: *{songs}*\n"
            "▶️ Total Plays: *{plays}*\n"
            "📅 Today's Plays: *{today}*\n"
            "💾 DB Size: *{size} KB*\n\n"
            "🔥 *Top Songs:*\n{top}\n"
            "⚡ *Energy:*\n{energy}"
        ),
        "admin_list_header": "📋 *Full Song List:*\n\n",
        "admin_list_empty": "📭 No songs in database.",
        "admin_list_line": "`{id}` — {title} — {artist} | ⚡{energy} | 🏷 {moods}\n",
        "broadcast_usage": "Usage: /broadcast [message]",
        "broadcast_no_users": "No users to broadcast to yet.",
        "broadcast_sending": "📣 Broadcasting to {count} users...",
        "broadcast_done": "📣 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}",

        # ── Home screen ───────────────────────────────────────────────────────
        "home_choose_mood": "Choose a mood or use the buttons below:",

        # ── Voice ─────────────────────────────────────────────────────────────
        "voice_processing": "🎙 Processing your voice message...",
        "voice_no_speech": "😔 Couldn't detect any speech. Please try again.",
        "voice_error": "❌ Failed to process voice message.",
        "voice_transcribed": "🎙 I heard: *{text}*\n\nSearching for a match...",

        # ── Mood auto-detection ────────────────────────────────────────────────
        "mood_detected_text": "🎭 Detected mood: *#{mood}*\n\nHere are some songs for you:",

        # ── Similar songs ─────────────────────────────────────────────────────
        "similar_btn": "🎵 Similar",
        "similar_header": "🎵 *Similar songs* to {title}:",
        "similar_none": "😔 No similar songs found yet.",

        # ── Radio mode ────────────────────────────────────────────────────────
        "radio_btn_next": "⏭ Next",
        "radio_btn_stop": "⏹ Stop",
        "radio_now_playing": "📻 *Radio* — Song {pos}/{total}",
        "radio_ended": "📻 Radio finished — no more songs in queue.",
        "radio_stopped": "⏹ Radio stopped.",
        "radio_queue_empty": "😔 No songs in the radio queue.",

        # ── Daily mix greetings ────────────────────────────────────────────────
        "daily_morning": "🌅 *Good morning!* Here's your daily mix to start the day:",
        "daily_noon": "☀️ *Good afternoon!* Here's your midday mix:",
        "daily_evening": "🌆 *Good evening!* Here's your mix for the evening:",
        "daily_night": "🌙 *Good night!* Here's a late-night mix for you:",

        # ── Search command ────────────────────────────────────────────────────
        "search_prompt": "🔍 What would you like to search for?\n\nType a song name, artist, or mood — or /cancel to exit.",
        "search_no_results": "😔 No results found for *{query}*.",
        "search_results_header": "🔍 Results for *{query}*:",
        "search_btn_play": "▶️ {title} — {artist}",
        "search_cancel": "🔍 Search cancelled.",

        # ── Playlists ─────────────────────────────────────────────────────────
        "playlist_add_btn": "➕ Playlist",
        "playlist_list_empty": "📭 You have no playlists yet.\n\nUse the *➕ Playlist* button on any song to create one!",
        "playlist_list_header": "📋 *Your Playlists:*\n",
        "playlist_item": "📁 *{name}* — {count} song(s)",
        "playlist_add_to_which": "📋 Add to which playlist?",
        "playlist_create_new_btn": "➕ Create New Playlist",
        "playlist_name_prompt": "📁 What would you like to name your new playlist?\n\n(or /cancel to exit)",
        "playlist_created": "✅ Playlist *{name}* created!",
        "playlist_added": "✅ Added to *{name}*!",
        "playlist_view_header": "📁 *{name}*\n",
        "playlist_view_empty": "📭 This playlist is empty.",
        "playlist_view_song": "  🎵 {title} — {artist}",
        "playlist_not_found": "❌ Playlist not found.",
        "playlist_cancel": "Cancelled.",

        # ── Admin panel (rich) ────────────────────────────────────────────────
        "admin_panel": (
            "👑 *MoodTunes Admin Panel*\n\n"
            "👥 Users: *{users}* (today: +{new_today} | week: +{new_week})\n"
            "🎵 Songs: *{songs}*\n"
            "▶️ Plays: today *{today_plays}* | week *{week_plays}* | total *{total_plays}*\n"
            "🔥 Most played: *{top_song}*\n"
            "🌊 Dominant mood today: *{top_mood}*\n"
            "🕐 Updated: {updated_at}\n\n"
            "📤 Send MP3 to add a song | /delete [id] | /edit [id]"
        ),
        "admin_stats_full": (
            "📊 *Full Admin Stats*\n\n"
            "👥 *Users*\n"
            "  Total: *{users}* | Today: +{new_today} | Week: +{new_week}\n"
            "  🇮🇷 FA: *{lang_fa}* | 🇬🇧 EN: *{lang_en}*\n\n"
            "🎵 *Songs* — {songs} total\n"
            "  {mood_counts}\n\n"
            "▶️ *Plays*\n"
            "  Today: *{today_plays}* | Week: *{week_plays}* | Month: *{month_plays}* | Total: *{total_plays}*\n\n"
            "🏆 *Top 5 Songs:*\n{top5}\n"
            "🆕 Last added: *{last_song}*\n"
            "💾 DB Size: *{size} KB*"
        ),

        # ── Edit song ─────────────────────────────────────────────────────────
        "admin_duplicate_song": (
            "⚠️ This song is already in the database!\n"
            "🎵 {title} — {artist}\n"
            "ID: #{id}"
        ),
        "edit_usage": "Usage: /edit [song_id]",
        "edit_song_panel": (
            "✏️ Editing song *#{id}*: *{title}* — {artist}\n\n"
            "Which field would you like to edit?"
        ),
        "edit_song_prompt_title":  "Send the new title:",
        "edit_song_prompt_artist": "Send the new artist name:",
        "edit_song_prompt_vibe":   "Send the new vibe label:",
        "edit_song_prompt_tags": (
            "Send new mood tags, comma-separated:\n"
            "(e.g.: happy, chill, romantic)\n\n"
            "Valid moods: happy sad chill energetic romantic nostalgic "
            "angry peaceful party focus workout melancholic"
        ),
        "edit_song_prompt_energy": "Send the new energy level:\n(low, medium, or high)",
        "edit_song_updated":   "✅ Updated!",
        "edit_song_deleted":   "✅ Deleted!",
        "edit_song_not_found": "❌ Song not found.",
        "edit_song_cancelled": "❌ Cancelled.",

        # ── Error messages ────────────────────────────────────────────────────
        "err_not_found": (
            "😔 *No songs found matching your request.*\n\n"
            "Try searching by mood, artist, or song name:"
        ),
        "err_db_empty": (
            "📭 *The music library is empty right now.*\n\n"
            "Check back soon — more songs are on the way!"
        ),
        "err_mood_empty": (
            "😔 *No songs in the `{mood}` mood yet.*\n\n"
            "Try another mood or listen to your daily mix:"
        ),
        "err_voice_failed": (
            "🎙 *Couldn't process your voice message.*\n\n"
            "You can try typing your search instead:"
        ),
        "err_api_busy": (
            "🤖 *AI is busy right now.*\n\n"
            "Please try again in a moment."
        ),
        "err_upload_failed": (
            "❌ *Failed to add song.*\n"
            "Error: `{error}`\n\n"
            "Please try uploading again."
        ),
        "err_radio_not_found": (
            "📻 *No songs found to start radio.*\n\n"
            "Try searching for a different song:"
        ),
        "err_general": (
            "⚠️ *Something went wrong.*\n\n"
            "Please try again or go back home."
        ),
    },

    "fa": {
        # ── Language selection ────────────────────────────────────────────────
        "language_select": (
            "🌍 Please choose your language:\n\n"
            "🇮🇷 فارسی - /lang_fa\n"
            "🇬🇧 English - /lang_en"
        ),
        "lang_set_en": "🇬🇧 Language set to English!",
        "lang_set_fa": "🇮🇷 زبان به فارسی تغییر کرد!",

        # ── Welcome ───────────────────────────────────────────────────────────
        "welcome": (
            "🎵 به MoodTunes خوش اومدی!\n"
            "اسم آهنگ یا حالت رو بفرست تا بهترین موزیک رو پیدا کنم!\n\n"
            "دستورات:\n"
            "/mood [حال] - موزیک بر اساس حال\n"
            "/radio [آهنگ] - آهنگ‌های مشابه\n"
            "/daily - میکس امروز\n"
            "/list - لیست آهنگ‌ها\n"
            "/stats - آمار من\n"
            "/language - تغییر زبان"
        ),

        # ── Search ────────────────────────────────────────────────────────────
        "searching": "🔍 دنبال *{query}* می‌گردم...",
        "found_db": "🎵 پیدا شد!\n🎭 ویب: _{vibe}_\n⚡ انرژی: {energy}",
        "found_ai": "🤖 بهترین تطابق: *{title}*\n🎭 ویب: _{vibe}_\n⚡ انرژی: {energy}",
        "not_found": "❌ پیدا نشد! /list رو بزن",

        # ── Mood ──────────────────────────────────────────────────────────────
        "mood_usage": "استفاده: /mood [حال]\n\nحال‌های موجود:\n{list}",
        "mood_invalid": "❌ حال `{mood}` نامعتبره.\n\nحال‌های موجود: {list}",
        "mood_header": "🌊 پلیست {mood} برات آماده شد:",
        "mood_empty": "😔 آهنگی برای حال `{mood}` پیدا نشد.",
        "mood_song_caption": "🎵 *{title}*\n👤 {artist}\n🎭 _{vibe}_",

        # ── Radio ─────────────────────────────────────────────────────────────
        "radio_usage": "استفاده: /radio [نام آهنگ یا هنرمند]",
        "radio_not_found": "❌ آهنگی با نام `{query}` پیدا نشد.",
        "radio_header": (
            "📻 رادیو بر اساس: {title} — {artist}\n"
            "🎭 ویب: _{vibe}_\n\n"
            "{count} آهنگ مشابه در راهه..."
        ),
        "radio_no_similar": "😔 *{title}* پیدا شد ولی آهنگ مشابهی نیست.",
        "radio_song_caption": "🎵 *{title}*\n👤 {artist}\n⚡ انرژی: {energy}",

        # ── Daily ─────────────────────────────────────────────────────────────
        "daily_header": "🌅 میکس امروز تو:",
        "daily_empty": "😔 کتابخانه خالیه. بعداً بیا!",
        "daily_song_caption": "🎵 *{title}*\n👤 {artist}\n🏷 {moods}",

        # ── List ──────────────────────────────────────────────────────────────
        "list_empty": "😔 هنوز آهنگی در کتابخانه نیست!",
        "list_header": "🎵 لیست آهنگ‌ها\n",
        "list_group_header": "*#{mood}* ({count} آهنگ)",
        "list_song_line": "  `{id}`. {title} — {artist} [{dur}]",

        # ── Stats ─────────────────────────────────────────────────────────────
        "stats_empty": (
            "📊 آمار تو\n\n"
            "هنوز آهنگی گوش ندادی.\n"
            "/daily یا /mood رو امتحان کن!"
        ),
        "stats_header": (
            "📊 آمار گوش دادن تو\n\n"
            "▶️ کل پخش: *{total}*\n"
            "💖 حال مورد علاقه: *{mood}*\n\n"
            "🏆 آهنگ‌های برتر:\n"
        ),
        "stats_no_top": "  هنوز چیزی نیست.",
        "stats_song_line": "  {i}. *{title}* — {artist} ({plays} بار)\n",

        # ── Admin (Persian) ───────────────────────────────────────────────────
        "admin_only": "⛔ فقط ادمین.",
        "admin_panel": (
            "👑 *پنل مدیریت MoodTunes*\n\n"
            "👥 کاربران: *{users}* (امروز: +{new_today} | هفته: +{new_week})\n"
            "🎵 آهنگ‌ها: *{songs}*\n"
            "▶️ پخش: امروز *{today_plays}* | هفته *{week_plays}* | کل *{total_plays}*\n"
            "🔥 پرپخش‌ترین: *{top_song}*\n"
            "🌊 حال غالب امروز: *{top_mood}*\n"
            "🕐 آپدیت: {updated_at}\n\n"
            "📤 MP3 بفرست تا اضافه کنم | /delete [id] | /edit [id]"
        ),
        "admin_stats_full": (
            "📊 *آمار کامل ادمین*\n\n"
            "👥 *کاربران*\n"
            "  کل: *{users}* | امروز: +{new_today} | هفته: +{new_week}\n"
            "  🇮🇷 FA: *{lang_fa}* | 🇬🇧 EN: *{lang_en}*\n\n"
            "🎵 *آهنگ‌ها* — {songs} تا\n"
            "  {mood_counts}\n\n"
            "▶️ *پخش‌ها*\n"
            "  امروز: *{today_plays}* | هفته: *{week_plays}* | ماه: *{month_plays}* | کل: *{total_plays}*\n\n"
            "🏆 *۵ آهنگ برتر:*\n{top5}\n"
            "🆕 آخرین اضافه: *{last_song}*\n"
            "💾 حجم DB: *{size} KB*"
        ),
        "admin_song_added": (
            "✅ آهنگ اضافه شد! (ID: `{id}`)\n\n"
            "🎵 *{title}* — {artist}\n"
            "🎭 ویب: _{vibe}_\n"
            "⚡ انرژی: *{energy}*\n"
            "🏷 حال‌ها: {moods}"
        ),
        "admin_analyzing": "🎵 در حال آنالیز *{title}* از *{artist}*...",
        "admin_song_failed": "❌ خطا در اضافه کردن آهنگ: {error}",
        "admin_delete_usage": "استفاده: /delete [song_id]",
        "admin_delete_invalid": "❌ ID نامعتبر. استفاده: /delete [song_id]",
        "admin_delete_not_found": "❌ آهنگ با ID {id} پیدا نشد.",
        "admin_delete_success": "✅ حذف شد: *{title}* از {artist}",
        "admin_delete_failed": "❌ حذف ناموفق بود.",
        "admin_stats": (
            "📊 آمار کامل:\n\n"
            "👥 کاربران: *{users}*\n"
            "🎵 آهنگ‌ها: *{songs}*\n"
            "▶️ کل پخش: *{plays}*\n"
            "📅 پخش امروز: *{today}*\n"
            "💾 حجم DB: *{size} KB*\n\n"
            "🔥 محبوب‌ترین:\n{top}\n"
            "⚡ انرژی:\n{energy}"
        ),
        "admin_list_header": "📋 لیست کامل:\n\n",
        "admin_list_empty": "📭 هنوز آهنگی نیست.",
        "admin_list_line": "`{id}` — {title} — {artist} | ⚡{energy} | 🏷 {moods}\n",
        "broadcast_usage": "استفاده: /broadcast [پیام]",
        "broadcast_no_users": "هنوز کاربری ثبت نشده.",
        "broadcast_sending": "📣 در حال ارسال به {count} کاربر...",
        "broadcast_done": "📣 ارسال کامل شد!\n✅ موفق: {sent}\n❌ ناموفق: {failed}",

        # ── Home screen ───────────────────────────────────────────────────────
        "home_choose_mood": "یه حال انتخاب کن یا از دکمه‌های زیر استفاده کن:",

        # ── Voice ─────────────────────────────────────────────────────────────
        "voice_processing": "🎙 در حال پردازش پیام صوتی...",
        "voice_no_speech": "😔 صحبتی تشخیص داده نشد. دوباره امتحان کن.",
        "voice_error": "❌ خطا در پردازش پیام صوتی.",
        "voice_transcribed": "🎙 شنیدم: *{text}*\n\nدنبال آهنگ مناسب می‌گردم...",

        # ── Mood auto-detection ────────────────────────────────────────────────
        "mood_detected_text": "🎭 حال تشخیص داده شده: *#{mood}*\n\nآهنگ‌های مناسب:",

        # ── Similar songs ─────────────────────────────────────────────────────
        "similar_btn": "🎵 مشابه",
        "similar_header": "🎵 *آهنگ‌های مشابه* با {title}:",
        "similar_none": "😔 هنوز آهنگ مشابهی پیدا نشد.",

        # ── Radio mode ────────────────────────────────────────────────────────
        "radio_btn_next": "⏭ بعدی",
        "radio_btn_stop": "⏹ توقف",
        "radio_now_playing": "📻 *رادیو* — آهنگ {pos}/{total}",
        "radio_ended": "📻 رادیو تموم شد — دیگه آهنگی نمونده.",
        "radio_stopped": "⏹ رادیو متوقف شد.",
        "radio_queue_empty": "😔 صف رادیو خالیه.",

        # ── Daily mix greetings ────────────────────────────────────────────────
        "daily_morning": "🌅 *صبح بخیر!* میکس امروز برای شروع روز:",
        "daily_noon": "☀️ *ظهر بخیر!* میکس ناهار:",
        "daily_evening": "🌆 *عصر بخیر!* میکس عصرانه:",
        "daily_night": "🌙 *شب بخیر!* میکس شبانه برات:",

        # ── Search command ────────────────────────────────────────────────────
        "search_prompt": "🔍 دنبال چی می‌گردی؟\n\nنام آهنگ، هنرمند یا حال بفرست — یا /cancel برای لغو.",
        "search_no_results": "😔 نتیجه‌ای برای *{query}* پیدا نشد.",
        "search_results_header": "🔍 نتایج *{query}*:",
        "search_btn_play": "▶️ {title} — {artist}",
        "search_cancel": "🔍 جستجو لغو شد.",

        # ── Playlists ─────────────────────────────────────────────────────────
        "playlist_add_btn": "➕ پلی‌لیست",
        "playlist_list_empty": "📭 هنوز پلی‌لیستی نداری.\n\nاز دکمه *➕ پلی‌لیست* روی هر آهنگ شروع کن!",
        "playlist_list_header": "📋 *پلی‌لیست‌های تو:*\n",
        "playlist_item": "📁 *{name}* — {count} آهنگ",
        "playlist_add_to_which": "📋 به کدوم پلی‌لیست اضافه کنم؟",
        "playlist_create_new_btn": "➕ پلی‌لیست جدید",
        "playlist_name_prompt": "📁 اسم پلی‌لیست جدیدت چیه؟\n\n(یا /cancel برای لغو)",
        "playlist_created": "✅ پلی‌لیست *{name}* ساخته شد!",
        "playlist_added": "✅ به *{name}* اضافه شد!",
        "playlist_view_header": "📁 *{name}*\n",
        "playlist_view_empty": "📭 این پلی‌لیست خالیه.",
        "playlist_view_song": "  🎵 {title} — {artist}",
        "playlist_not_found": "❌ پلی‌لیست پیدا نشد.",
        "playlist_cancel": "لغو شد.",

        # ── Edit song ─────────────────────────────────────────────────────────
        "admin_duplicate_song": (
            "⚠️ این آهنگ قبلاً توی دیتابیس هست!\n"
            "🎵 {title} — {artist}\n"
            "شناسه: #{id}"
        ),
        "edit_usage": "استفاده: /edit [song_id]",
        "edit_song_panel": (
            "✏️ ویرایش آهنگ *#{id}*: *{title}* — {artist}\n\n"
            "کدوم فیلد رو ویرایش کنم؟"
        ),
        "edit_song_prompt_title":  "عنوان جدید رو بفرست:",
        "edit_song_prompt_artist": "نام هنرمند جدید رو بفرست:",
        "edit_song_prompt_vibe":   "ویب جدید رو بفرست:",
        "edit_song_prompt_tags": (
            "تگ‌های جدید رو با کاما جدا بفرست:\n"
            "(مثال: happy, chill, romantic)\n\n"
            "حال‌های معتبر: happy sad chill energetic romantic nostalgic "
            "angry peaceful party focus workout melancholic"
        ),
        "edit_song_prompt_energy": "انرژی جدید رو بفرست:\n(low، medium یا high)",
        "edit_song_updated":   "✅ آپدیت شد!",
        "edit_song_deleted":   "✅ حذف شد!",
        "edit_song_not_found": "❌ آهنگ پیدا نشد.",
        "edit_song_cancelled": "❌ لغو شد.",

        # ── Error messages ────────────────────────────────────────────────────
        "err_not_found": (
            "😔 *آهنگی پیدا نشد.*\n\n"
            "با حال، هنرمند یا نام آهنگ امتحان کن:"
        ),
        "err_db_empty": (
            "📭 *کتابخانه موزیک فعلاً خالیه.*\n\n"
            "به زودی آهنگ‌های جدید اضافه می‌شه!"
        ),
        "err_mood_empty": (
            "😔 *هنوز آهنگی با حال `{mood}` نداریم.*\n\n"
            "یه حال دیگه امتحان کن یا میکس روزانه گوش بده:"
        ),
        "err_voice_failed": (
            "🎙 *پیام صوتیت پردازش نشد.*\n\n"
            "می‌تونی متنی جستجو کنی:"
        ),
        "err_api_busy": (
            "🤖 *هوش مصنوعی الان مشغوله.*\n\n"
            "یه لحظه صبر کن و دوباره امتحان کن."
        ),
        "err_upload_failed": (
            "❌ *آهنگ اضافه نشد.*\n"
            "خطا: `{error}`\n\n"
            "دوباره آپلود کن."
        ),
        "err_radio_not_found": (
            "📻 *آهنگی برای شروع رادیو پیدا نشد.*\n\n"
            "یه آهنگ دیگه جستجو کن:"
        ),
        "err_general": (
            "⚠️ *یه مشکلی پیش اومد.*\n\n"
            "دوباره امتحان کن یا برو خونه."
        ),
    },
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated string. Falls back to English if key missing."""
    strings = STRINGS.get(lang, STRINGS["en"])
    template = strings.get(key) or STRINGS["en"].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
