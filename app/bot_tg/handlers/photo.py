"""
app/bot_tg/handlers/photo.py

What will happens when a photo will received by the bot
"""

from telegram import Update
from telegram.ext import ContextTypes


async def photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message

    if message is None:
        return

    # Get caption, if any
    caption = message.caption

    # Get the largest/best available photo
    best_photo = message.photo[-1]

    # Telegram file_id
    file_id = best_photo.file_id
    # Build the caption instead of printing
    caption = (
        "✨ <b>Photo Information</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Caption</b>\n"
        f"└ {message.caption or '<i>None</i>'}\n\n"
        f"🆔 <b>File ID</b>\n"
        f"└ <code>{file_id}</code>\n\n"
        f"📏 <b>Dimensions</b>\n"
        f"└ <code>{best_photo.width} × {best_photo.height}</code>\n\n"
        f"📦 <b>File Size</b>\n"
        f"└ <code>{best_photo.file_size} bytes</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 <b>Want to turn this image into a video?</b>\n"
        "🎵 <b>Want to create a song from your image?</b>\n\n"
        "⭐ <b>Subscribe to our Pro Plan</b>\n"
        "👑 Or <b>contact the admins</b> for more information.\n\n"
        "🚀 <i>Unlock more powerful AI features with Pro!</i>"
    )
    await message.reply_photo(
        photo=file_id,
        caption=caption,
    )
