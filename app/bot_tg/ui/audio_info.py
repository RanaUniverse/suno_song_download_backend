"""
app/bot_tg/ui/audio_info.py

Here i will write some logics of how to shows what informations
to the users of different audio related thigns?
"""

from datetime import timedelta


from telegram import Audio, PhotoSize, Message


from ..utils import escape_html_or_default

#


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
    Format the main audio metadata from telegram api.
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
        f"├ <b>Title:</b> {escape_html_or_default(audio.title)}\n"
        f"├ <b>Performer:</b> {escape_html_or_default(audio.performer)}\n"
        f"├ <b>Filename:</b> {escape_html_or_default(audio.file_name)}\n"
        f"├ <b>MIME Type:</b> {escape_html_or_default(audio.mime_type)}\n"
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
