"""
app/shared/song_info.py

This has some basic things which i will write here and
then use htis in different places
"""

from dataclasses import dataclass
import re
import json


import requests

from app.config import settings


@dataclass
class SunoSongFrontendData:
    """
    song_url_by_id is the consistant url of the song
    i should to use this and keep store this and the id also
    """

    id: str = ""
    title: str = ""
    artist: str = ""
    artist_username: str = ""
    image_url: str = ""
    private_audio_url: str = ""
    duration: str = ""
    duration_in_seconds: int | None = None
    created_date: str = ""
    plays: int | None = None
    likes: int | None = None
    song_url: str = ""
    song_url_by_id: str = ""

    # Optional: A handy method to convert it back to a dict if template or JSON needs it
    def to_dict(self) -> dict[str, str | int | None]:
        """
        Converts the dataclass back to a dictionary for templates or JSON responses."""
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "artist_username": self.artist_username,
            "image_url": self.image_url,
            "audio_url": self.private_audio_url,
            "duration": self.duration,
            "duration_in_seconds": self.duration_in_seconds,
            "created_date": self.created_date,
            "plays": self.plays,
            "likes": self.likes,
            "song_url": self.song_url,
            "song_url_by_id": self.song_url_by_id,
        }


def collect_payload(html: str):
    """
    Replicates the JavaScript collectPayload function to grab Next.js flight chunks.
    """
    pattern = r'self\.__next_f\.push\(\[\s*1\s*,\s*"((?:\\.|[^"\\])*)"\s*\]\)'
    matches = re.findall(pattern, html)
    out = ""
    for m in matches:
        try:
            # Safely unescape the string literal
            decoded = json.loads(f'"{m}"')
            out += decoded
        except Exception:
            out += m.replace(r"\"", '"').replace(r"\\", "\\").replace(r"\n", "\n")
    return out


def fetch_suno_song_data_advanced(
    target_song_url: str,
) -> SunoSongFrontendData:
    """
    This is a Normal Sync Function so i need to call this in async way

    Advanced helper that extracts clean titles and artist names from the HTML title tag,
    gathers deep stats (duration, plays, likes, created date) from the Next.js payload,
    and returns a fully populated SunoSongData dataclass.

    This i think to use to shows the song information to the user
    on bot page after my python will loads the song data
    """
    song_id = ""
    title = ""
    artist = ""
    artist_username = ""
    duration_str = ""
    duration_secs = None
    created_date = ""
    plays_count = None
    likes_count = None

    if not target_song_url:
        return SunoSongFrontendData()

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        }

        resp = requests.get(
            target_song_url,
            headers=headers,
            allow_redirects=True,
            timeout=5,
        )

        if resp.status_code == 200:
            html = resp.text
            final_url = resp.url

            # 1. Extract Song UUID
            uuid_pattern = (
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            )
            id_match = re.search(uuid_pattern, final_url, re.IGNORECASE)
            if not id_match:
                id_match = re.search(uuid_pattern, html, re.IGNORECASE)

            song_id = id_match.group(0).lower() if id_match else ""

            # 2. Extract Title and Artist cleanly from the HTML <title> tag
            # Example: "QvTake Me Back by T. K. AHMAD | Suno"
            title_match = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
            if title_match:
                raw_title = title_match.group(1)

                # Strip off trailing " | Suno" first
                cleaned_title_part = re.sub(r"\s*\|\s*Suno\s*$", "", raw_title).strip()

                # Split by " by " to separate Song Title and Artist Name
                if " by " in cleaned_title_part:
                    parts = cleaned_title_part.split(" by ")
                    title = parts[0].strip()
                    artist = parts[-1].strip()
                else:
                    title = cleaned_title_part

            # 3. Collect Next.js Flight Payload for deep stats
            payload = collect_payload(html)

            # 4. Extract Username Handle (e.g. "tkahmad")
            handle_match = re.search(r'"handle"\s*:\s*"([^"]+)"', payload)
            if handle_match:
                artist_username = handle_match.group(1)

            # 4. Extract Duration (Seconds and formatted MM:SS)
            dur_match = re.search(r'"duration"\s*:\s*([0-9.]+)', payload)
            if dur_match:
                secs = float(dur_match.group(1))
                duration_secs = round(secs)
                mins = int(duration_secs // 60)
                rem = int(duration_secs % 60)
                duration_str = f"{mins}:{rem:02d}"

            # 5. Extract Created Date (YYYY-MM-DD)
            date_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', payload)
            if date_match:
                created_date = date_match.group(1)[:10]

            # 6. Extract Plays & Likes
            plays_match = re.search(r'"play_count"\s*:\s*(\d+)', payload)
            if plays_match:
                plays_count = int(plays_match.group(1))

            likes_match = re.search(r'"upvote_count"\s*:\s*(\d+)', payload)
            if likes_match:
                likes_count = int(likes_match.group(1))

    except Exception as e:
        print(f"❌ Failed to parse advanced metadata server-side: {e}")

    # Return a fully populated SunoSongData dataclass instance
    canonical_link = f"https://suno.com/song/{song_id}" if song_id else ""
    song_data = SunoSongFrontendData(
        id=song_id,
        title=title,
        artist=artist,
        artist_username=artist_username,  # 👈 Populated here!
        image_url=f"https://cdn2.suno.ai/image_{song_id}.jpeg" if song_id else "",
        private_audio_url=f"https://cdn1.suno.ai/{song_id}.mp3" if song_id else "",
        duration=duration_str,
        duration_in_seconds=duration_secs,
        created_date=created_date,
        plays=plays_count,
        likes=likes_count,
        song_url=target_song_url,
        song_url_by_id=canonical_link,
    )
    print(song_data)
    return song_data


def calculate_song_cost(
    song_data: SunoSongFrontendData,
) -> int | None:
    """
    Determines how many Stars it will cost to later donwload this song

    I will also want when the threshold second is 0 it means that
    all song are free of cost :haha
    """

    if song_data.duration_in_seconds is None:
        return settings.song.long_cost

    if settings.song.duration_threshold_seconds == 0:
        return None

    if song_data.duration_in_seconds <= settings.song.duration_threshold_seconds:
        return settings.song.short_cost
    else:
        return settings.song.long_cost
