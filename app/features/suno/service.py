"""
app/features/suno/service.py

Basic suno related services will be here which will my main entrypoint
of this suno maybe i think like this

This will have mainly the song download function
"""

from app.features.suno_downloader import SunoScraper
from app.features.suno.models import SongInfo


def download_suno_song(
    info: SongInfo,
    # song_link: str,
    output_dir: str = "downloads",
) -> str | None:
    scraper = SunoScraper()

    try:
        result = scraper.download_song(
            info,
            output_dir=output_dir,
            audio_format="m4a",  # or "mp3" / "wav"
        )
        return result.audio_path

    except Exception:
        return None
