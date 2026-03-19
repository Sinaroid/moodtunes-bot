import json
import logging
import os
import anthropic

logger = logging.getLogger(__name__)

VALID_MOODS = {
    "happy", "sad", "chill", "energetic", "romantic", "nostalgic",
    "angry", "peaceful", "party", "focus", "workout", "melancholic"
}

ANALYSIS_PROMPT = """Analyze the song: "{title}" by {artist}. Return ONLY a JSON object:
{{
  "mood": ["tag1","tag2"],
  "vibe_label": "short evocative description (max 80 chars)",
  "energy": "low|medium|high",
  "language": "persian|english|arabic|turkish|other",
  "tempo": "slow|mid|fast",
  "rhythm": "soft|steady|driving|swing",
  "lyrics_theme": "love|party|spiritual|social|personal|nature|other",
  "vocal_style": "melodic|rap|electronic|instrumental|folk|classical",
  "decade": "60s|70s|80s|90s|2000s|2010s|2020s",
  "similar_artists": ["artist1","artist2"]
}}

Mood tags (use 1-3 only): happy, sad, chill, energetic, romantic, nostalgic, angry, peaceful, party, focus, workout, melancholic
Energy: exactly low, medium, or high
All other fields: use only the exact values listed
Return ONLY the JSON object, no other text."""

MOOD_DETECT_PROMPT = """The user sent this message: "{text}"

Does this message express or request a specific music mood?
If yes, respond with ONLY one of these exact tags:
happy, sad, chill, energetic, romantic, nostalgic, angry, peaceful, party, focus, workout, melancholic

If the message is about a song title, artist name, or is unrelated to mood, respond with exactly: none"""

SEARCH_PROMPT = """A user searched for: "{query}"

From the songs in our database, find the best match:
{songs_list}

Return ONLY a JSON object:
{{"match_id": <song_id_or_null>, "reason": "brief reason"}}

If no good match exists, set match_id to null."""


VALID_LANGUAGES = {"persian", "english", "arabic", "turkish", "other"}
VALID_TEMPOS = {"slow", "mid", "fast"}
VALID_RHYTHMS = {"soft", "steady", "driving", "swing"}
VALID_THEMES = {"love", "party", "spiritual", "social", "personal", "nature", "other"}
VALID_VOCAL_STYLES = {"melodic", "rap", "electronic", "instrumental", "folk", "classical"}
VALID_DECADES = {"60s", "70s", "80s", "90s", "2000s", "2010s", "2020s"}


async def analyze_song_vibe(title: str, artist: str) -> dict:
    """Call Claude API to analyze a song's mood, vibe, and DJ metadata."""
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = ANALYSIS_PROMPT.format(title=title, artist=artist)

    try:
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        # Extract JSON if wrapped in code blocks
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)

        # Validate core fields
        moods = [m for m in data.get("mood", []) if m in VALID_MOODS]
        if not moods:
            moods = ["chill"]

        energy = data.get("energy", "medium").lower()
        if energy not in ("low", "medium", "high"):
            energy = "medium"

        vibe_label = str(data.get("vibe_label", ""))[:100]

        # Validate extended fields (None if invalid/missing)
        language = data.get("language", "").lower()
        language = language if language in VALID_LANGUAGES else None

        tempo = data.get("tempo", "").lower()
        tempo = tempo if tempo in VALID_TEMPOS else None

        rhythm = data.get("rhythm", "").lower()
        rhythm = rhythm if rhythm in VALID_RHYTHMS else None

        lyrics_theme = data.get("lyrics_theme", "").lower()
        lyrics_theme = lyrics_theme if lyrics_theme in VALID_THEMES else None

        vocal_style = data.get("vocal_style", "").lower()
        vocal_style = vocal_style if vocal_style in VALID_VOCAL_STYLES else None

        decade = data.get("decade", "").lower()
        decade = decade if decade in VALID_DECADES else None

        similar_artists = data.get("similar_artists", [])
        if not isinstance(similar_artists, list):
            similar_artists = []

        return {
            "mood": moods,
            "vibe_label": vibe_label,
            "energy": energy,
            "language": language,
            "tempo": tempo,
            "rhythm": rhythm,
            "lyrics_theme": lyrics_theme,
            "vocal_style": vocal_style,
            "decade": decade,
            "similar_artists": similar_artists,
        }

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Claude response for {title} by {artist}: {e}")
        return {"mood": ["chill"], "vibe_label": f"{title} by {artist}", "energy": "medium"}
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error analyzing {title} by {artist}: {e}")
        return {"mood": ["chill"], "vibe_label": f"{title} by {artist}", "energy": "medium"}


async def detect_mood_from_text(text: str) -> str | None:
    """Return a mood tag if text implies a mood, else None."""
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    try:
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=20,
            messages=[{"role": "user", "content": MOOD_DETECT_PROMPT.format(text=text)}]
        )
        result = response.content[0].text.strip().lower()
        if result in VALID_MOODS:
            return result
        return None
    except Exception as e:
        logger.error(f"Mood detection error: {e}")
        return None


async def find_best_match(query: str, songs: list[dict]) -> dict | None:
    """Use Claude to find the best matching song for a text query."""
    if not songs:
        return None

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    songs_list = "\n".join(
        f"ID {s['id']}: \"{s['title']}\" by {s['artist']} | mood: {', '.join(s['mood'])} | vibe: {s['vibe_label']}"
        for s in songs
    )

    prompt = SEARCH_PROMPT.format(query=query, songs_list=songs_list)

    try:
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
        match_id = data.get("match_id")

        if match_id is None:
            return None

        for song in songs:
            if song["id"] == int(match_id):
                return song

        return None

    except Exception as e:
        logger.error(f"Claude search failed for query '{query}': {e}")
        return None
