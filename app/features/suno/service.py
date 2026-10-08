"""
app/features/suno/service.py

Basic suno related services will be here which will my main entrypoint
of this suno maybe i think like this

This will have mainly the song download function
"""

from app.features.suno_downloader import SunoScraper


def download_suno_song(
    song_link: str,
    output_dir: str = "downloads",
) -> str | None:
    scraper = SunoScraper()

    try:
        result = scraper.download_song(
            song_link,
            output_dir=output_dir,
            audio_format="m4a",  # or "mp3" / "wav"
        )
        return result["audio_path"]
    except Exception:
        return None


def main():
    """
    Below is the example of how to use this
    """

    song_link = "https://suno.com/s/xGMsb9CspedVbECW"
    song_link = "https://suno.com/hook/f0a5d387-4ee3-4cb8-a61a-217312ed4905"
    path = download_suno_song(song_link)

    if path:
        print("Downloaded:", path)
    else:
        print("Download failed")


if __name__ == "__main__":
    main()
