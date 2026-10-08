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


class AudioSampleResult(BaseModel):
    """Details of a sample created from a local audio file."""

    sample_path: str
    filename: str
    total_duration: float
    start_sec: float
    duration_sec: float
    actual_sample_duration: float


class SampleDownloadResult(AudioSampleResult):
    """Details of a sample downloaded directly from a Suno song."""

    info: SongInfo
    cover_path: str | None = None
    format: str


class DownloadResult(BaseModel):
    """Details of a completed full-song download."""

    info: SongInfo
    audio_path: str
    format: str
    duration: float
    cover_path: str | None = None
    metadata_path: str | None = None
    m4a_path: str | None = None
