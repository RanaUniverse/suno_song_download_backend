"""
app/shared/song_info.py

This has some basic things which i will write here and
then use htis in different places
"""

from app.config import settings

from app.features.suno.models import SongInfo

#


def calculate_song_cost(
    song_info: SongInfo,
) -> int | None:
    """
    Determines how many Stars it will cost to later donwload this song

    I will also want when the threshold second is 0 it means that
    all song are free of cost :haha
    """

    if song_info.duration_in_seconds is None:
        return settings.song.long_cost

    if settings.song.duration_threshold_seconds == 0:
        return None

    if song_info.duration_in_seconds <= settings.song.duration_threshold_seconds:
        return settings.song.short_cost
    else:
        return settings.song.long_cost
