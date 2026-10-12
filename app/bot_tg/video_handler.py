"""
app/bot_tg/video_handler.py

Receive a video from the user and send the same video back.
Reuse Telegram's file_id instead of downloading and uploading it again.
"""

from telegram import Update
from telegram.ext import ContextTypes


async def get_video_file_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message
    print(update)

    if message is None or message.video is None:
        return

    video = message.video
    caption = f"{message.caption}\n" f"FIle id is\n" f"{message.video.file_id}"  # type: ignore

    await message.reply_video(
        video=video.file_id,
        caption=caption,
        caption_entities=message.caption_entities,
    )
