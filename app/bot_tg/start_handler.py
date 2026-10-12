"""
app/bot_tg/start_handler.py

This will mainly defines what the start reply need to give to
the user when user start htis the logic will be here
"""

from telegram import Update, User, InlineKeyboardMarkup
from telegram.error import TelegramError


from telegram.ext import (
    ContextTypes,
)

from app.config import settings
from app.shared.logger_related import RanaLogger

from .text_formatter import (
    get_welcome_message,
    get_telegram_verification_failed_message,
    get_telegram_verification_success_message,
)
from app.config import settings

from .keyboards import generate_buttons_for_attach_with_song

SONG_FORWARD_GROUP_ID = settings.bot.song_forward_group_id


async def send_new_user_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    user: User,
) -> bool:
    channel_id = SONG_FORWARD_GROUP_ID

    if not channel_id:
        RanaLogger.warning("Cannot notify channel: channel ID is not configured.")
        return False

    try:
        # Escape the user's name because we're using HTML parse mode.
        import html

        safe_name = html.escape(user.full_name)

        text = (
            "👤 <b>New User Started the Bot</b>\n\n"
            f"👤 <b>Name:</b> {safe_name}\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"🔗 <b>Profile:</b> "
            f'<a href="tg://user?id={user.id}">Open User Profile</a>'
        )

        await context.bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        RanaLogger.info(f"New user notification sent to channel: {user.id}")

        return True

    except TelegramError as e:
        RanaLogger.warning(f"Failed to send new user notification: {e}")
        return False


def verify_user_with_payload_value(
    payload: str,
    user_id: int,
) -> bool:
    """
    For now as user_id is in the payload i will check this easily
    later i will add redis and so on for use this goodly
    """
    if payload == f"{user_id}":
        return True
    else:
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        RanaLogger.error("Could not retrieve effective user , message from update.")
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
    # await context.bot.send_message(
    #     text=txt,
    #     chat_id=user.id,
    # )
    buttons = generate_buttons_for_attach_with_song()
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

    await send_new_user_to_channel(
        context=context,
        user=user,
    )
