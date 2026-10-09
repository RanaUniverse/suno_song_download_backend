"""Validated data models shared by the Suno feature."""

from typing import Literal


from pydantic import BaseModel, Field

#


class SongInfo(BaseModel):
    """
    Metadata extracted from a Suno song page.
    """

    id: str
    type: Literal["hook", "song"] = Field(
        default="song",
        description=(
            "mostly it will songs, but for hook shorts video i will "
            "need another logic so i keep like this"
        ),
    )

    title: str = "Suno AI Song"
    prompt: str | None = None
    tags: str | None = None
    source_url: str = Field(
        description="The final url this song will open by ",
    )
    audio_url: str | None = None
    image_url: str | None = None
    video_url: str | None = Field(
        description="This is for hook songs",
        default=None,
    )


class ResolvedSunoLink(BaseModel):
    type: Literal["song", "hook"]
    content_id: str

    @property
    def full_url(self) -> str:
        """
        From the large song_id this will make the final
        redirected like url here at last
        """
        return f"https://suno.com/{self.type}/{self.content_id}"


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


class SeparationResult(BaseModel):
    """Details of separated instrumental and vocal audio tracks."""

    instrumental_path: str
    vocals_path: str
    instrumental_filename: str
    vocals_filename: str
    duration: float
    format: Literal["m4a", "mp3", "wav"]
