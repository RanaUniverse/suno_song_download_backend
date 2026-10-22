"""
app/bot_tg/thumbnail.py
"""

from pathlib import Path

from app.config import settings

# from app.features.suno.models import SongInfo


def get_audio_thumbnail(
    # song_data: SongInfo,
    audio_path: Path,
) -> Path | None:
    """
    Select the thumbnail to use when sending audio through Telegram.

    Returns:
        Path: The selected thumbnail image.
        None: No custom thumbnail should be sent.
    """

    mode = settings.bot.audio_thumbnail_mode

    if mode == "none":
        return None

    if mode == "brand":
        brand_path = settings.bot.audio_thumbnail_brand_path

        if brand_path.is_file():
            return brand_path

        return None

    if mode == "song":
        # if the structer of the image will change i will need
        # below line to change later
        song_thumbnail = audio_path.with_suffix(".jpeg")

        if song_thumbnail.is_file():
            return song_thumbnail

        # If the song thumbnail is unavailable, fall back
        # to the brand logo.
        brand_path = settings.bot.audio_thumbnail_brand_path

        if brand_path.is_file():
            return brand_path

        return None

    return None
