import traceback
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
        return result.audio_path  # 👈 Use dot notation for Pydantic models!
    except Exception as e:
        print(f"\n❌ Exception details: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


def main():
    song_link = "https://suno.com/song/11e26b83-ed16-425f-824b-9500240576b4"
    song_link = "https://suno.com/s/T7GIvQDqjkk8bMJ2"

    print(f"Testing link: {song_link} ...")
    path = download_suno_song(song_link)

    if path:
        print("✅ Downloaded successfully to:", path)
    else:
        print("❌ Download failed")


if __name__ == "__main__":
    main()