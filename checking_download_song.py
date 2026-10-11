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
        print(
            f"\n❌ Exception details: {type(e).__name__}: {e}",
        )
        traceback.print_exc()
        return None


# Suno song links
SHORT_SONG = "https://suno.com/s/cbDOEH5feyWw6oEF"
LARGE_SONG = "https://suno.com/song/5dfd3531-6092-43a9-ab50-e9335c8ad39f"

# Suno hook links
SHORT_HOOK = "https://suno.com/s/T7GIvQDqjkk8bMJ2"
LARGE_HOOK = "https://suno.com/hook/f0a5d387-4ee3-4cb8-a61a-217312ed4905"


def main():
    # song_link=""
    song_link = SHORT_SONG
    song_link = LARGE_SONG
    song_link = SHORT_HOOK
    song_link = LARGE_HOOK

    print(f"Testing link: {song_link} ...")
    path = download_suno_song(song_link)

    if path:
        print("✅ Downloaded successfully to:", path)
    else:
        print("❌ Download failed")


if __name__ == "__main__":
    main()
