"""Validated data models shared by the Suno feature."""

from pydantic import BaseModel


class SongInfo(BaseModel):
    """Metadata extracted from a Suno song page."""

    id: str
    title: str = "Suno AI Song"
    audio_url: str | None = None
    image_url: str | None = None
    prompt: str = ""
    tags: str = ""
    source_url: str
