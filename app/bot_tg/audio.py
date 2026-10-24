"""
app/bot_tg/audio.py

This will say what will happens after user will send audio
"""

import html

from datetime import timedelta

from telegram import (
    Audio,
    Update,
    PhotoSize,
    Message,
)

from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.config import settings
from app.features.suno.models import SongInfo
from app.shared.logger_related import RanaLogger

from .text_formatter import (
    generate_song_details_only,
)

#
SONG_FORWARD_GROUP_ID = settings.bot.song_forward_group_id


def format_file_size(size: int | None) -> str:
    """
    it will take the audio file id from the telegram
    audio's file_size that is in bytes and it will say in MB
    """
    if size is None:
        return "Not provided by Telegram"

    size_mb = size / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def format_duration(duration: int | timedelta) -> str:
    """
    Format audio duration as HH:MM:SS
    """
    if isinstance(duration, timedelta):
        duration = int(duration.total_seconds())

    if duration <= 0:
        return "⚠️ 00:00 — Duration Unavailable By Telegram"

    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    return f"{minutes:02}:{seconds:02}"


def format_audio_info(audio: Audio) -> str:
    """
    Format the main audio metadata.
    """

    duration_warning = ""

    if audio.duration == 0:
        duration_warning = (
            "\n\n⚠️ <b>Duration Warning</b>\n"
            "Please check this song again. Telegram reported "
            "a duration of 0 seconds."
        )

    return (
        "🎵 <b>Audio File Information</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"├ <b>Title:</b> {safe_value(audio.title)}\n"
        f"├ <b>Performer:</b> {safe_value(audio.performer)}\n"
        f"├ <b>Filename:</b> {safe_value(audio.file_name)}\n"
        f"├ <b>MIME Type:</b> {safe_value(audio.mime_type)}\n"
        f"├ <b>Duration:</b> {format_duration(audio.duration)}\n"
        f"└ <b>File Size:</b> {format_file_size(audio.file_size)}"
        f"{duration_warning}"
    )


def format_thumbnail_info(thumbnail: PhotoSize | None) -> str:
    """Format thumbnail metadata for a Telegram HTML message."""
    if thumbnail is None:
        return (
            "🖼️ <b>Album Thumbnail</b>\n"
            "└ <b>Available:</b> No thumbnail provided by Telegram"
        )

    return (
        "🖼️ <b>Album Thumbnail</b>\n"
        "├ <b>Available:</b> Yes\n"
        f"├ <b>Width:</b> {thumbnail.width} px\n"
        f"└ <b>Height:</b> {thumbnail.height} px"
    )


def format_message_info(message: Message) -> str:
    """Format Telegram message metadata."""
    return (
        "💬 <b>Message Information</b>\n"
        f"├ <b>Chat ID:</b> <code>{message.chat_id}</code>\n"
        f"├ <b>Message ID:</b> <code>{message.message_id}</code>\n"
    )


def safe_value(value: object | None) -> str:
    """
    Escape metadata for Telegram HTML messages.
    """
    if value is None or value == "":
        return "Not provided by Telegram"

    return html.escape(str(value))


async def audio_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Reply with the metadata of an incoming Telegram audio file.
    This will return the data comes from the BOT Api not from file codec
    """

    message = update.effective_message

    if message is None:
        return

    audio = message.audio

    if audio is None:
        await message.reply_text(
            "Please send an audio file as Telegram audio.",
        )
        return

    metadata = (
        f"{format_audio_info(audio)}\n"
        f"{format_thumbnail_info(thumbnail=audio.thumbnail)}\n\n"
        f"{format_message_info(message)}\n"
        "🆔 <b>Telegram File Identifiers</b>\n"
        f"└ <b>Unique File ID:</b>\n"
        f"<code>{safe_value(audio.file_unique_id)}</code>\n"
        f"├ <b>File ID:</b>\n<code>{safe_value(audio.file_id)}</code>\n"
    )

    try:
        await message.reply_text(
            text=metadata,
            do_quote=True,
        )
        RanaLogger.info(
            f"Audio metadata sent for chat_id={message.chat_id}, "
            f"file_id={audio.file_id}"
        )

    except Exception:
        RanaLogger.exception(
            f"Failed to send audio metadata for chat_id={message.chat_id}"
        )
        raise


async def forward_song_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    audio_file_id: str,
    user_name: str,
    song_data: SongInfo | None = None,
    is_merge_audio: bool = False,
    merged_song_count: int | None = None,
) -> bool:
    """
    Forward an already-uploaded Telegram audio file to the configured
    song channel.

    Returns:
        True: song was successfully sent
        False: forwarding was skipped or failed
    """

    # Forwarding is disabled/not configured
    if not SONG_FORWARD_GROUP_ID:
        RanaLogger.info("Song forwarding is disabled: no channel ID configured.")
        return False

    try:
        if is_merge_audio:
            caption = (
                f"🎧 <b>Merged Audio</b>\n\n"
                f"👤 <b>Merged by:</b> {user_name}\n"
                f"🎵 <b>Songs merged:</b> {merged_song_count or 'Unknown'}"
            )
        else:
            caption = (
                f"🎵 <b>Song downloaded by:</b> {user_name}\n\n"
                f"{generate_song_details_only(song_data) if song_data else ''}\n"
            )

        await context.bot.send_audio(
            audio=audio_file_id,
            chat_id=SONG_FORWARD_GROUP_ID,
            caption=caption,
        )

        RanaLogger.info(
            f"Song successfully forwarded to channel. "
            f"channel_id={SONG_FORWARD_GROUP_ID}, "
            f"file_id={audio_file_id}"
        )

        return True

    except TelegramError as e:
        RanaLogger.warning(
            f"Failed to forward song to channel " f"{SONG_FORWARD_GROUP_ID}: {e}"
        )
        return False
