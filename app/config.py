"""
app/config.py

Here i will keep the config related things of different useful
private and useful data
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import (
    # AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
)

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

SUPPORTED_AUDIO_FORMAT = ("m4a", "mp3", "wav")
AudioFormat = Literal[
    "m4a",
    "mp3",
    "wav",
]
ThumbnailMode = Literal[
    "song",
    "brand",
    "none",
]


class WebAppSettings(BaseModel):
    """
    Here i will keep flask/fastapi
    app related things to run
    """

    host: str = "0.0.0.0"
    port: int = 9999
    debug: bool = False
    secret_key: SecretStr
    login_backend: Literal[
        "SQLMODEL",
        "MONGODB",
        "MEMORY",
    ]
    validation_mode: Literal[
        "DEVELOPMENT",
        "PRODUCTION",
    ] = "DEVELOPMENT"

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "https://SunoAisongDownload.online",
        "https://sunoaisongdownload.online",
        "https://www.sunoaisongdownload.online",
    ]


class MailAddressSettings(BaseModel):
    """
    All the email address which need to be given
    in different case i will keep those here
    """

    # This from email should be match in the coresponding provider
    from_email_default: EmailStr

    reply_to_default: EmailStr | None = Field(default=None, repr=False)


class MailSettings(BaseModel):
    """
    Email related configuraiton will be here
    username and password i will get to login
    and from email is my email id other will see
    """

    provider: Literal[
        "local",
        "smtp",
    ]
    # how i can say it value will only, "local" or "smtp"

    host: str
    port: int
    username: str
    password: SecretStr
    security: Literal[
        "ssl",
        "starttls",
    ]

    address: MailAddressSettings


class OTPSettings(BaseModel):

    backend: Literal[
        "local",
        "redis",
    ]


class RedisSettings(BaseModel):
    """
    Redis config will be here
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0

    username: str | None = None
    password: SecretStr | None = None

    # If provided, this takes priority over host,port,etc.
    url: str | None = None


class DatabaseSettings(BaseModel):
    """
    Database related maybe i will use postgres or sqlite
    so their configurations i will write here

    For Sqlite i will just use the default things.
    For Postgres i will use all the username, password,
    host, port, name should be given
    """

    backend: Literal[
        "sqlite",
        "postgres",
    ] = "sqlite"

    sqlite_filename: str = "local_database.db"

    username: str | None = None
    password: SecretStr | None = None
    host: str | None = None
    port: int | None = None
    name: str | None = None

    @property
    def db_url(self) -> str:
        if self.backend == "postgres":
            if (
                self.username is None
                or self.password is None
                or self.host is None
                or self.port is None
                or self.name is None
            ):
                raise RuntimeError(
                    f"For Postgresql the value of all DB "
                    "Connections this must be not None",
                )

            POSTGRES_URL = (
                f"postgresql+psycopg2://"
                f"{self.username}:"
                f"{self.password.get_secret_value()}@"
                f"{self.host}:"
                f"{self.port}/"
                f"{self.name}"
            )
            return POSTGRES_URL

        elif self.backend == "sqlite":
            sqlite_filepath = self.sqlite_filename
            SQLITE_URL = f"sqlite:///" f"{sqlite_filepath}"
            return SQLITE_URL

        else:
            raise RuntimeError(
                "Database should be sqlite or postgres for now",
            )


class BotSettings(BaseModel):
    """
    Bot Configuration Settings will be here defines the values
    for the bot to run there
    """

    token: SecretStr
    username: str | None = Field(
        default=None,
        description="If I want to specefy the username of the bot i "
        "will write without the @ symbol",
    )
    start_image_file_id: str | None = Field(
        default=None,
        description="I want to shows user a basic startup message on "
        "/start the file id will be here, if not given i need to setup "
        "the not sending the image",
    )
    start_video_file_id: str | None = Field(
        default=None,
        description="A sample video to shows user hot to use",
    )
    song_forward_group_id: int | None = Field(
        default=-1004300343847,
        description="if there is group id then i will forword the thigns "
        "to this group",
    )
    help_account_username: str

    default_song_format: AudioFormat = Field(
        default="m4a",
        description="The format of song my bot will send to user is this",
    )

    instant_song_send: bool = Field(
        default=True,
        description=(
            "By this my backend will check if to download "
            "the song instantly after a user send a link to download a song."
        ),
    )

    health_check_notify_enabled: bool = Field(
        default=True,
        description="Send Telegram notifications when the health endpoint is accessed.",
    )
    health_check_notify_chat_id: int | None = Field(
        default=8176162859,
        description="This say where the response should to send ",
    )
    web_download_notify_enabled: bool = Field(
        default=True,
        description="Alert the admin chat and upload songs to song_forward_group_id "
        "when someone downloads through the website.",
    )

    audio_thumbnail_mode: ThumbnailMode = Field(
        default="song",
        description=(
            "Thumbnail mode for audio sent through Telegram: "
            "'song' uses the song's thumbnail, "
            "'brand' uses the bot's brand logo, "
            "'none' sends no custom thumbnail."
        ),
    )

    audio_thumbnail_brand_path: Path = Field(
        # default=Path("static/RanaUniverseLogoForThumbnailTelegramBot.png"),
        description=(
            "Filesystem path to the brand logo used as an "
            "audio thumbnail when audio_thumbnail_mode='brand'."
        ),
    )
    show_song_caption: bool = Field(
        default=True,
        description="If it will shows song caption or not will be useful "
        "for custom bot of other user so that they will not have problem",
    )


class SongSettings(BaseModel):
    duration_threshold_seconds: int = Field(
        default=180,
        description="Duration in seconds used to determine whether a song is short or long.",
    )

    short_cost: int = 2
    long_cost: int = 3

    cost_applicable: bool = Field(
        default=False,
        description="Whether downloading a song costs credits.",
    )

    download_automatic: bool = Field(
        default=True,
        description="Whether songs should be downloaded automatically.",
    )


class AudioMergeSettings(BaseModel):
    """Configuration for merging audio files in Telegram."""

    enabled: bool = Field(
        default=True,
        description="Whether audio merging is enabled.",
    )

    min_files: int = Field(
        default=2,
        ge=2,
        description="Minimum number of audio files required for merging.",
    )

    max_files: int = Field(
        default=20,
        ge=2,
        description="Maximum number of audio files allowed in one merge.",
    )

    work_dir: Path = Field(
        default=Path("downloads/merge_audio"),
        description="Directory used to store temporary merge files.",
    )


class PathSettings(BaseModel):
    log_filename: str = "LogFile.log"
    data_foldername: str = "data"


class ExternalSettings(BaseModel):
    suno_target_domain: str = "suno.com"

    razorpay_profile_link: str = "https://razorpay.me/@RanaUniverse"
    paypal_profile_link: str = "https://paypal.me/RanaUniverse321"
    my_donation_website: str = "https://donate_money.Rana49.online"
    suno_song_create_link: str = "https://suno.com/create"
    my_email_id: str = "RanaUniverse321+tg_bot_help@gmail.com"


class SunoSettings(BaseModel):
    base_url: str = "https://suno.com"

    home_urls: tuple[str, ...] = (
        "https://suno.com",
        "http://suno.com",
        "https://suno.ai",
        "http://suno.ai",
    )

    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    accept: str = (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    )
    accept_language: str = "es-ES,es;q=0.9,en;q=0.8"

    @property
    def default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

    @property
    def share_api_headers(self) -> dict[str, str]:
        """
        i will use this headers for resolve the url or id
        mainly form this website
        f"https://studio-api.prod.suno.com/api/share/code/{share_code}",
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }


class Settings(BaseSettings):
    """
    db: DatabaseSettings = DatabaseSettings()
    I give this because when not any default values set for the db
    it will make the class instance and use this values there!
    """

    owner_name: str

    bot: BotSettings
    song: SongSettings
    data_path: PathSettings
    external: ExternalSettings

    app: WebAppSettings
    otp: OTPSettings
    mail: MailSettings = Field(repr=False)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    audio_merge: AudioMergeSettings = Field(default_factory=AudioMergeSettings)
    redis: RedisSettings
    suno: SunoSettings = Field(default_factory=SunoSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )


@lru_cache
def get_settings() -> Settings:
    """
    i will use this to get my values
    """
    return Settings()  # type: ignore


settings = get_settings()

if __name__ == "__main__":

    print("xxx")
    print(settings.db.db_url)
    print("yyy")
