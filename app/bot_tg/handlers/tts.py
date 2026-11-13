"""
app/bot_tg/handlers/tts.py

See here i will try to make how to handle the text to speech
"""

import html


from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.features.tts.service import text_to_speech
from app.shared.logger_related import RanaLogger
from app.config import settings

from ..constants import StickerFileId
from ..services.notifications import notify_text_to_audio_generated
from ..services.thumbnail import get_audio_thumbnail
from ..ui.keyboards import (
    generate_dynamic_keyboard,
)

#


MAX_TTS_CHARS = settings.bot.max_tts_chars


async def handle_text_to_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        RanaLogger.warning(
            "Message, user must present on handle text to voice",
        )
        return

    if len(text) > MAX_TTS_CHARS:
        await message.reply_text(
            f"Text too long (max {MAX_TTS_CHARS} characters) Use Premium Bot To Make Large 30 Minute Long Songs."
        )
        return

    # later i will check from other place what to use
    voice = (
        "bn-IN-TanishaaNeural" if has_bengali(text) else "en-IN-NeerjaExpressiveNeural"
    )

    wait_msg = await message.reply_text(
        "🎙 Generating Your Song, Please wait...",
        do_quote=True,
    )

    audio_path = None
    try:
        processing_sticker = await message.reply_sticker(StickerFileId.LIGHTNING)
        audio_path = await text_to_speech(text, user_id=user.id, voice=voice)
        with open(audio_path, "rb") as f:
            buttons = generate_dynamic_keyboard("www.sunoaisongdownload.online")
            send_audio = await message.reply_audio(
                reply_markup=InlineKeyboardMarkup(buttons),
                audio=f,
                do_quote=True,
                thumbnail=get_audio_thumbnail(),
            )
            if send_audio:
                user_mention = (
                    f'<a href="tg://user?id={user.id}">'
                    f"{html.escape(user.full_name)}</a>"
                )
                await notify_text_to_audio_generated(
                    bot=context.bot,
                    audio_file_id=send_audio.audio.file_id,  # type: ignore
                    user_name=f"{user_mention}",
                    source_text=text,
                )

    except Exception as e:
        RanaLogger.error(f"TTS failed for {user.id}: {e}")
        await message.reply_text(
            "❌ Couldn't generate the Song. Please try again or contact Admin."
        )

    finally:
        await wait_msg.delete()
        if audio_path:
            audio_path.unlink(missing_ok=True)

        await processing_sticker.delete()


def has_bengali(text: str) -> bool:
    return any("\u0980" <= ch <= "\u09ff" for ch in text)
