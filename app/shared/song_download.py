"""
app/shared/song_download.py

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

    song_link = "https://suno.com/s/xGMsb9CspedVbECW"
    path = download_suno_song(song_link)

    if path:
        print("Downloaded:", path)
    else:
        print("Download failed")


if __name__ == "__main__":
    main()
