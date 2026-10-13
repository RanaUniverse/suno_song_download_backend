"""
app/features/suno/storage.py

"""

from pathlib import Path
import re


import requests


from .models import SongInfo

from app.shared.logger_related import RanaLogger

#


def sanitize_filename(name: str) -> str:
    """
    Cleans unauthorized characters in file names.
    """
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace("\n", " ").replace("\r", "")
    return clean[:90] if clean else "suno_song"


def get_base_name(info: SongInfo) -> str:
    """
    Build Constinent filename for the stem for the audio and images
    """
    clean_title = sanitize_filename(info.title)
    song_id = info.id or "default_track"
    return f"{clean_title} ({song_id})"


def download_cover_image(
    info: SongInfo,
    destination_folder: str | Path | None = None,
    session: requests.Session | None = None,
) -> Path | None:
    """
    Download a cover image from an already-known URL.
    When i will call this form any session i will use that session.
    """
    if not info.image_url:
        RanaLogger.warning(
            f"Image link should present for download image, {info.image_url}"
        )
        return None

    if not destination_folder:
        RanaLogger.warning(
            f"Image is not saving due to miss of destination "
            "path of {info.image_url}"
        )
        return None

    # Avoid accidentally saving an HTML error page as an image.

    client = session or requests.Session()
    response = client.get(info.image_url, timeout=10)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if not content_type.startswith("image/"):
        RanaLogger.error(
            f"Expected an image response, got "
            f"{content_type or f'unknown content type for {info.image_url}'}"
        )
        return None

    cover_ext = ".jpeg" if ".jpeg" in info.image_url else ".png"

    destination = Path(destination_folder) / f"{get_base_name(info)}{cover_ext}"

    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_bytes(response.content)

    return destination
