"""
app/features/suno/models_hook.py

"""

from datetime import datetime

from pydantic import BaseModel, Field, AliasChoices


class ClipMetadata(BaseModel):
    prompt: str = ""
    tags: str = ""


class Clip(BaseModel):
    title: str = Field(
        description="The Title in the Hook shows large upper of the creator name",
        default="Suno AI Song",
    )

    play_count: int
    upvote_count: int

    metadata: ClipMetadata = ClipMetadata()
    audio_image_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("image_url"),
        description="The Large Main Audio File's Thumbnail's image",
    )
    created_time: datetime = Field(
        validation_alias=AliasChoices("created_at"),
        description="The time when this song is made is in this clip present here",
    )


class HookResponse(BaseModel):
    id: str = Field(
        description="This is the large uuid of the my main hook song",
    )
    base_audio_id: str | None = Field(
        description=(
            "One song has many hook, so the main song's id will be "
            "here, thsi will be a song not hook anymore"
        ),
        validation_alias=AliasChoices("original_clip_id"),
    )

    video_length: float | None = Field(
        default=None,
        validation_alias=AliasChoices("video_duration"),
        description="The Short Hook Video Length will shows here",
    )

    video_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("rendered_video_url"),
        description="This is the Short Hook Video link downloadable",
    )

    thumbnail_image_url: str | None = Field(
        default=None,
        description="This is the thumbnail for the hook short video",
    )
    clip: Clip

    @property
    def base_audio_url(
        self,
    ) -> str:
        return f"https://suno.com/song/{self.base_audio_id}"
