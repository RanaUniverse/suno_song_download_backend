"""
app/bot_tg/start_handler.py

This will mainly defines what the start reply need to give to
the user when user start htis the logic will be here
"""

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
)


from app.config import settings
from app.shared.logger_related import RanaLogger


from ...ui.text_formatter import (
    get_welcome_message,
    get_telegram_verification_failed_message,
    get_telegram_verification_success_message,
)

from ...ui.keyboards import generate_dynamic_keyboard

from ...services.notifications import notify_new_user

#


def verify_user_with_payload_value(
    payload: str,
    user_id: int,
) -> bool:
    """
    i will use this for different type of refer by another user

    For now as user_id is in the payload i will check this easily
    later i will add redis and so on for use this goodly
    """
    if payload == f"web_app_from_{user_id}":
        return True
    else:
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        RanaLogger.error(
            "Could not retrieve effective user , message from update.",
        )
        return

    payload = context.args[0] if context.args else None

    if payload:
        verified = verify_user_with_payload_value(
            payload=payload,
            user_id=user.id,
        )
        if verified:
            txt = get_telegram_verification_success_message()
        else:
            txt = get_telegram_verification_failed_message()

        await message.reply_text(text=txt)
        return

    txt = get_welcome_message(
        full_name=user.full_name,
    )

    buttons = generate_dynamic_keyboard()
    reply_markup = InlineKeyboardMarkup(buttons)

    if settings.bot.start_video_file_id:
        await message.reply_video(
            video=settings.bot.start_video_file_id,
            caption=txt,
            do_quote=True,
            reply_markup=reply_markup,
            show_caption_above_media=True,
        )
    else:
        await message.reply_text(
            text=txt,
            do_quote=True,
            reply_markup=reply_markup,
        )

    await notify_new_user(
        bot=context.bot,
        user=user,
    )
