"""
app/bot_tg/download_handlers.py

"""

"""
app/bot_tg/downloads_handler.py

Handles the /downloads command.

For now there is no login system, so every user gets the
"please login or buy premium" message. Later, when accounts exist,
the logged-in branch will show how many songs the user downloaded.
"""

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.shared.logger_related import RanaLogger

from .text_formatter import (
    get_not_logged_in_message,
    get_downloads_count_message,
)
from .keyboards import generate_login_premium_keyboard


async def get_user_account(user_id: int) -> None:
    """
    Placeholder. Later this will check your DB/Redis for a logged-in
    account and return something like {"downloads_count": 100, "is_premium": True}.
    Returns None while there is no login system.
    """
    return None


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        RanaLogger.error("Could not retrieve effective user, message from update.")
        return

    account = await get_user_account(user_id=user.id)

    # Not logged in (this is always the case for now)
    if account is None:
        await message.reply_text(
            text=get_not_logged_in_message(),
            do_quote=True,
            reply_markup=InlineKeyboardMarkup(generate_login_premium_keyboard()),
        )
        return

    # Logged in (future)
    await message.reply_text(
        text=get_downloads_count_message(
            count=account["downloads_count"],
        ),
        do_quote=True,
    )
