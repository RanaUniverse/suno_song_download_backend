"""
app/bot_tg/thumbnail.py
"""

from pathlib import Path

from app.config import settings

# from app.features.suno.models import SongInfo

# app/bot_tg/services/thumbnail.py
from pathlib import Path

from app.config import settings


def _brand_thumbnail() -> Path | None:
    path = settings.bot.audio_thumbnail_brand_path
    return path if path.is_file() else None


def _song_thumbnail(audio_path: Path) -> Path | None:
    # Change this suffix if the saved cover image format ever changes.
    path = audio_path.with_suffix(".jpeg")
    return path if path.is_file() else None


def get_audio_thumbnail(audio_path: Path | None = None) -> Path | None:
    """
    Pick the thumbnail to send with an audio message.

    Modes (settings.bot.audio_thumbnail_mode):
      "none"  -> no thumbnail
      "brand" -> always the brand logo
      "song"  -> the song's own cover, falling back to the brand logo
                 (merged audio has no cover, so it also gets the logo)
    """
    mode = settings.bot.audio_thumbnail_mode

    if mode == "brand":
        return _brand_thumbnail()

    if mode == "song":
        if audio_path is not None:
            return _song_thumbnail(audio_path) or _brand_thumbnail()
        return _brand_thumbnail()

    return None
