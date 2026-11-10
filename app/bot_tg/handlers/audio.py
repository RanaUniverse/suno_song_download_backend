"""
app/bot_tg/handlers/audio.py

This will decide What will happens when user will send a audio
to the bot will will do what will be by this.
"""

from telegram import (
    Update,
)

from telegram.ext import ContextTypes


from app.config import settings
from app.shared.logger_related import RanaLogger


from ..ui.audio_info import (
    format_audio_info,
    format_message_info,
    format_thumbnail_info,
)
from ..utils import escape_html_or_default

#


SONG_FORWARD_GROUP_ID = settings.bot.song_forward_group_id


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
        f"<code>{escape_html_or_default(audio.file_unique_id)}</code>\n"
        f"├ <b>File ID:</b>\n<code>{escape_html_or_default(audio.file_id)}</code>\n"
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
