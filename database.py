import aiosqlite
import json
import logging
import os
import random
from datetime import datetime
from typing import Optional

DB_PATH = "songs.db"
logger = logging.getLogger(__name__)


class DuplicateSongError(Exception):
    """Raised when trying to add a song that already exists in the DB."""
    def __init__(self, song_id: int, title: str, artist: str):
        self.song_id = song_id
        self.title = title
        self.artist = artist
        super().__init__(f"Duplicate: #{song_id} {title} – {artist}")


# ── Backend abstraction (aiosqlite ↔ Turso/libsql) ───────────────────────────

_turso_client = None


def _use_turso() -> bool:
    return bool(os.getenv("TURSO_URL"))


async def _get_turso():
    global _turso_client
    if _turso_client is None:
        import libsql_client
        url = os.getenv("TURSO_URL", "")
        # libsql_client requires https:// — convert libsql:// scheme
        url = url.replace("libsql://", "https://")
        token = os.getenv("TURSO_AUTH_TOKEN", "")
        _turso_client = libsql_client.create_client(url=url, auth_token=token)
    return _turso_client


async def _query(sql: str, params=None) -> list[dict]:
    """Execute SELECT → list of dicts."""
    params = list(params) if params else []
    if _use_turso():
        client = await _get_turso()
        rs = await client.execute(sql, params)
        cols = list(rs.columns)
        return [dict(zip(cols, row)) for row in rs.rows]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def _queryone(sql: str, params=None) -> Optional[dict]:
    """Execute SELECT → first row as dict, or None."""
    rows = await _query(sql, params)
    return rows[0] if rows else None


async def _queryval(sql: str, params=None):
    """Execute SELECT → first column of first row, or None."""
    params = list(params) if params else []
    if _use_turso():
        client = await _get_turso()
        rs = await client.execute(sql, params)
        return rs.rows[0][0] if rs.rows else None
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
        return row[0] if row else None


async def _insert(sql: str, params=None) -> int:
    """Execute INSERT → lastrowid."""
    params = list(params) if params else []
    if _use_turso():
        client = await _get_turso()
        rs = await client.execute(sql, params)
        return rs.last_insert_rowid or 0
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, params)
        await db.commit()
        return cur.lastrowid or 0


async def _modify(sql: str, params=None) -> int:
    """Execute UPDATE/DELETE → rows affected."""
    params = list(params) if params else []
    if _use_turso():
        client = await _get_turso()
        rs = await client.execute(sql, params)
        return rs.rows_affected or 0
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, params)
        await db.commit()
        return cur.rowcount or 0


async def _tx(statements: list) -> None:
    """Execute multiple statements atomically."""
    if _use_turso():
        import libsql_client
        client = await _get_turso()
        await client.batch([
            libsql_client.Statement(sql, list(p) if p else [])
            for sql, p in statements
        ])
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            for sql, params in statements:
                await db.execute(sql, params or [])
            await db.commit()


async def _ddl(sql: str, ignore_error: bool = False) -> None:
    """Execute DDL (CREATE TABLE, ALTER TABLE, CREATE INDEX)."""
    try:
        if _use_turso():
            client = await _get_turso()
            await client.execute(sql)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(sql)
                await db.commit()
    except Exception as e:
        if not ignore_error:
            raise


# ── Schema ────────────────────────────────────────────────────────────────────

async def init_db():
    await _ddl("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            file_id TEXT NOT NULL UNIQUE,
            duration INTEGER DEFAULT 0,
            mood TEXT DEFAULT '[]',
            vibe_label TEXT DEFAULT '',
            energy TEXT DEFAULT 'medium',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _ddl("""
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            song_id INTEGER NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    """)
    await _ddl("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id   INTEGER PRIMARY KEY,
            language  TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _ddl("CREATE INDEX IF NOT EXISTS idx_play_history_user ON play_history(user_id)")
    await _ddl("CREATE INDEX IF NOT EXISTS idx_play_history_song ON play_history(song_id)")
    await _ddl("""
        CREATE TABLE IF NOT EXISTS radio_queues (
            user_id  INTEGER PRIMARY KEY,
            song_ids TEXT NOT NULL DEFAULT '[]',
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _ddl("""
        CREATE TABLE IF NOT EXISTS playlists (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            name       TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _ddl("""
        CREATE TABLE IF NOT EXISTS playlist_songs (
            playlist_id INTEGER NOT NULL,
            song_id     INTEGER NOT NULL,
            added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (playlist_id, song_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (song_id)     REFERENCES songs(id)     ON DELETE CASCADE
        )
    """)

    # ── Migrations (safe to run multiple times) ──────────────────────────
    for col, definition in [
        ("play_count",        "INTEGER DEFAULT 0"),
        ("added_by",          "TEXT"),
        ("last_played",       "TIMESTAMP"),
        ("language",          "TEXT"),
        ("tempo",             "TEXT"),
        ("rhythm",            "TEXT"),
        ("lyrics_theme",      "TEXT"),
        ("vocal_style",       "TEXT"),
        ("decade",            "TEXT"),
        ("similarity_vector", "TEXT"),
    ]:
        await _ddl(f"ALTER TABLE songs ADD COLUMN {col} {definition}", ignore_error=True)

    logger.info("Database initialized%s.", " (Turso)" if _use_turso() else "")


# ── Song operations ───────────────────────────────────────────────────────────

async def add_song(title: str, artist: str, file_id: str, duration: int,
                   mood: list, vibe_label: str, energy: str,
                   added_by: str = None,
                   language: str = None, tempo: str = None, rhythm: str = None,
                   lyrics_theme: str = None, vocal_style: str = None,
                   decade: str = None) -> int:
    existing = await _queryone(
        "SELECT id, title, artist FROM songs "
        "WHERE LOWER(title) = LOWER(?) AND LOWER(artist) = LOWER(?)",
        [title, artist]
    )
    if existing:
        raise DuplicateSongError(existing["id"], existing["title"], existing["artist"])

    return await _insert(
        """INSERT INTO songs
           (title, artist, file_id, duration, mood, vibe_label, energy, added_by,
            language, tempo, rhythm, lyrics_theme, vocal_style, decade)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [title, artist, file_id, duration, json.dumps(mood), vibe_label, energy, added_by,
         language, tempo, rhythm, lyrics_theme, vocal_style, decade]
    )


async def delete_song(song_id: int) -> bool:
    return await _modify("DELETE FROM songs WHERE id = ?", [song_id]) > 0


async def get_all_songs() -> list[dict]:
    rows = await _query("SELECT * FROM songs ORDER BY added_at DESC")
    return [_parse_song(r) for r in rows]


async def get_song_by_id(song_id: int) -> Optional[dict]:
    row = await _queryone("SELECT * FROM songs WHERE id = ?", [song_id])
    return _parse_song(row) if row else None


async def get_songs_by_mood(mood_tag: str, limit: int = 5) -> list[dict]:
    rows = await _query(
        "SELECT * FROM songs WHERE mood LIKE ? ORDER BY RANDOM() LIMIT ?",
        [f'%"{mood_tag}"%', limit]
    )
    return [_parse_song(r) for r in rows]


async def get_songs_by_vibe(vibe_label: str, energy: str, exclude_id: int, limit: int = 5) -> list[dict]:
    rows = await _query(
        """SELECT * FROM songs
           WHERE id != ? AND (energy = ? OR vibe_label LIKE ?)
           ORDER BY RANDOM() LIMIT ?""",
        [exclude_id, energy, f"%{vibe_label[:10]}%", limit]
    )
    return [_parse_song(r) for r in rows]


async def get_random_songs_varied(limit: int = 3) -> list[dict]:
    all_songs = await get_all_songs()
    if not all_songs:
        return []
    seen_moods: set = set()
    result = []
    random.shuffle(all_songs)
    for song in all_songs:
        moods = tuple(song["mood"])
        if moods not in seen_moods:
            seen_moods.add(moods)
            result.append(song)
            if len(result) >= limit:
                break
    if len(result) < limit:
        for song in all_songs:
            if song not in result:
                result.append(song)
                if len(result) >= limit:
                    break
    return result[:limit]


async def search_songs(query: str) -> list[dict]:
    rows = await _query(
        """SELECT * FROM songs
           WHERE title LIKE ? OR artist LIKE ? OR vibe_label LIKE ?
           ORDER BY added_at DESC LIMIT 10""",
        [f"%{query}%", f"%{query}%", f"%{query}%"]
    )
    return [_parse_song(r) for r in rows]


def _parse_song(d: dict) -> dict:
    d["mood"] = json.loads(d["mood"]) if d.get("mood") else []
    return d


# ── Play history ──────────────────────────────────────────────────────────────

async def log_play(user_id: int, song_id: int):
    await _tx([
        ("INSERT INTO play_history (user_id, song_id) VALUES (?, ?)", [user_id, song_id]),
        ("UPDATE songs SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP WHERE id = ?", [song_id]),
        ("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", [user_id]),
    ])


# ── User settings ─────────────────────────────────────────────────────────────

async def get_user_language(user_id: int) -> Optional[str]:
    row = await _queryone(
        "SELECT language FROM user_settings WHERE user_id = ?", [user_id]
    )
    if row is None or row.get("language") is None:
        return None
    return row["language"]


async def get_effective_lang(user_id: int) -> str:
    lang = await get_user_language(user_id)
    return lang if lang else "en"


async def set_user_language(user_id: int, language: str):
    await _modify(
        """INSERT INTO user_settings (user_id, language)
           VALUES (?, ?)
           ON CONFLICT(user_id) DO UPDATE SET language = excluded.language""",
        [user_id, language]
    )


async def is_new_user(user_id: int) -> bool:
    lang = await get_user_language(user_id)
    return lang is None


async def get_all_user_ids() -> list[int]:
    rows = await _query(
        "SELECT DISTINCT user_id FROM user_settings "
        "UNION SELECT DISTINCT user_id FROM play_history"
    )
    return [r["user_id"] for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_user_stats(user_id: int) -> dict:
    total = await _queryval(
        "SELECT COUNT(*) FROM play_history WHERE user_id = ?", [user_id]
    ) or 0

    top_rows = await _query(
        """SELECT s.title, s.artist, COUNT(*) as plays
           FROM play_history ph JOIN songs s ON ph.song_id = s.id
           WHERE ph.user_id = ?
           GROUP BY ph.song_id ORDER BY plays DESC LIMIT 3""",
        [user_id]
    )

    mood_rows = await _query(
        """SELECT s.mood FROM play_history ph JOIN songs s ON ph.song_id = s.id
           WHERE ph.user_id = ?""",
        [user_id]
    )

    mood_counts: dict = {}
    for row in mood_rows:
        moods = json.loads(row["mood"]) if row.get("mood") else []
        for m in moods:
            mood_counts[m] = mood_counts.get(m, 0) + 1
    top_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "N/A"

    return {
        "total_plays": total,
        "top_songs": [{"title": r["title"], "artist": r["artist"], "plays": r["plays"]} for r in top_rows],
        "favorite_mood": top_mood,
    }


async def get_admin_stats() -> dict:
    total_songs = await _queryval("SELECT COUNT(*) FROM songs") or 0
    total_users = await _queryval("SELECT COUNT(*) FROM user_settings") or 0
    total_plays = await _queryval("SELECT COUNT(*) FROM play_history") or 0
    today_plays = await _queryval(
        "SELECT COUNT(*) FROM play_history WHERE DATE(played_at) = DATE('now')"
    ) or 0
    plays_week = await _queryval(
        "SELECT COUNT(*) FROM play_history WHERE played_at >= DATE('now', '-7 days')"
    ) or 0
    plays_month = await _queryval(
        "SELECT COUNT(*) FROM play_history WHERE played_at >= DATE('now', '-30 days')"
    ) or 0
    new_users_today = await _queryval(
        "SELECT COUNT(*) FROM user_settings WHERE DATE(created_at) = DATE('now')"
    ) or 0
    new_users_week = await _queryval(
        "SELECT COUNT(*) FROM user_settings WHERE created_at >= DATE('now', '-7 days')"
    ) or 0

    top_songs_rows = await _query(
        """SELECT s.title, s.artist, COUNT(*) as plays
           FROM play_history ph JOIN songs s ON ph.song_id = s.id
           GROUP BY ph.song_id ORDER BY plays DESC LIMIT 5"""
    )
    top_songs = [{"title": r["title"], "artist": r["artist"], "plays": r["plays"]} for r in top_songs_rows]

    # Songs by language
    lang_rows = await _query("SELECT language, COUNT(*) as cnt FROM songs GROUP BY language")
    lang_breakdown = {(r["language"] or "other"): r["cnt"] for r in lang_rows}

    # Songs by mood (parsed from JSON in Python)
    mood_song_rows = await _query("SELECT mood FROM songs")
    mood_counts: dict = {}
    for row in mood_song_rows:
        moods = json.loads(row["mood"]) if row.get("mood") else []
        for m in moods:
            mood_counts[m] = mood_counts.get(m, 0) + 1

    # Top mood today
    today_mood_rows = await _query(
        """SELECT s.mood FROM play_history ph
           JOIN songs s ON ph.song_id = s.id
           WHERE DATE(ph.played_at) = DATE('now')"""
    )
    today_mood_counts: dict = {}
    for row in today_mood_rows:
        moods = json.loads(row["mood"]) if row.get("mood") else []
        for m in moods:
            today_mood_counts[m] = today_mood_counts.get(m, 0) + 1
    top_mood_today = max(today_mood_counts, key=today_mood_counts.get) if today_mood_counts else "—"

    # Top song (single string)
    top_song_row = top_songs[0] if top_songs else None
    top_song_str = f"{top_song_row['title']} — {top_song_row['artist']} ({top_song_row['plays']}x)" \
        if top_song_row else "—"

    # Last song added
    last_song = await _queryone(
        "SELECT title, artist, added_at FROM songs ORDER BY added_at DESC LIMIT 1"
    )

    # Energy distribution
    energy_rows = await _query("SELECT energy, COUNT(*) as cnt FROM songs GROUP BY energy")
    energy_dist = {r["energy"]: r["cnt"] for r in energy_rows}

    db_size_kb = 0
    if not _use_turso():
        try:
            db_size_kb = os.path.getsize(DB_PATH) // 1024
        except OSError:
            pass

    return {
        "total_songs": total_songs,
        "total_users": total_users,
        "new_users_today": new_users_today,
        "new_users_week": new_users_week,
        "total_plays": total_plays,
        "today_plays": today_plays,
        "plays_week": plays_week,
        "plays_month": plays_month,
        "db_size_kb": db_size_kb,
        "top_songs": top_songs,
        "top_song_str": top_song_str,
        "lang_breakdown": lang_breakdown,
        "mood_counts": mood_counts,
        "top_mood_today": top_mood_today,
        "last_song": last_song,
        "energy_distribution": energy_dist,
    }


# ── Radio queue ───────────────────────────────────────────────────────────────

async def set_radio_queue(user_id: int, song_ids: list[int], position: int = 0):
    await _modify(
        """INSERT INTO radio_queues (user_id, song_ids, position)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET song_ids=excluded.song_ids, position=excluded.position""",
        [user_id, json.dumps(song_ids), position]
    )


async def get_radio_queue(user_id: int) -> Optional[dict]:
    row = await _queryone(
        "SELECT song_ids, position FROM radio_queues WHERE user_id = ?", [user_id]
    )
    if not row:
        return None
    return {"song_ids": json.loads(row["song_ids"]), "position": row["position"]}


async def advance_radio_queue(user_id: int) -> Optional[int]:
    queue = await get_radio_queue(user_id)
    if not queue:
        return None
    new_pos = queue["position"] + 1
    song_ids = queue["song_ids"]
    if new_pos >= len(song_ids):
        await clear_radio_queue(user_id)
        return None
    await _modify(
        "UPDATE radio_queues SET position = ? WHERE user_id = ?", [new_pos, user_id]
    )
    return song_ids[new_pos]


async def clear_radio_queue(user_id: int):
    await _modify("DELETE FROM radio_queues WHERE user_id = ?", [user_id])


# ── Playlists ─────────────────────────────────────────────────────────────────

async def get_user_playlists(user_id: int) -> list[dict]:
    return await _query(
        "SELECT id, name, created_at FROM playlists WHERE user_id = ? ORDER BY created_at DESC",
        [user_id]
    )


async def create_playlist(user_id: int, name: str) -> int:
    return await _insert(
        "INSERT INTO playlists (user_id, name) VALUES (?, ?)", [user_id, name]
    )


async def get_playlist_by_id(playlist_id: int) -> Optional[dict]:
    return await _queryone(
        "SELECT id, user_id, name FROM playlists WHERE id = ?", [playlist_id]
    )


async def add_song_to_playlist(playlist_id: int, song_id: int):
    await _modify(
        "INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id) VALUES (?, ?)",
        [playlist_id, song_id]
    )


async def get_playlist_songs(playlist_id: int) -> list[dict]:
    rows = await _query(
        """SELECT s.* FROM songs s
           JOIN playlist_songs ps ON s.id = ps.song_id
           WHERE ps.playlist_id = ?
           ORDER BY ps.added_at DESC""",
        [playlist_id]
    )
    return [_parse_song(r) for r in rows]


async def delete_playlist(playlist_id: int):
    await _modify("DELETE FROM playlists WHERE id = ?", [playlist_id])


# ── Song field updates ────────────────────────────────────────────────────────

async def update_song_extended_fields(song_id: int, fields: dict) -> bool:
    allowed = {"language", "tempo", "rhythm", "lyrics_theme", "vocal_style", "decade", "similarity_vector"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [song_id]
    return await _modify(f"UPDATE songs SET {set_clause} WHERE id = ?", values) > 0


async def get_songs_needing_reanalysis() -> list[dict]:
    rows = await _query("SELECT * FROM songs WHERE language IS NULL ORDER BY id")
    return [_parse_song(r) for r in rows]


async def update_song_field(song_id: int, field: str, value) -> bool:
    allowed = {"title", "artist", "vibe_label", "energy", "mood"}
    if field not in allowed:
        return False
    if field == "mood" and isinstance(value, list):
        value = json.dumps(value)
    return await _modify(f"UPDATE songs SET {field} = ? WHERE id = ?", [value, song_id]) > 0
