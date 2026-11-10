"""
app/bot_tg/basic_commands.py

This will handle some basic commands of the bot like
/settings /help and so on
"""

from telegram import Update


from telegram.ext import (
    ContextTypes,
)


from ...ui.text_formatter import (
    about_text,
    help_text,
    settings_text,
    token_text,
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Provides help instructions for using the bot.
    """

    message = update.effective_message
    if not message:
        return

    await message.reply_text(help_text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tells the user about the project and web app connection.
    """
    message = update.effective_message
    if not message:
        return

    await message.reply_text(about_text)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Placeholder for managing user settings.
    """
    message = update.effective_message
    if not message:
        return

    await message.reply_text(settings_text)


async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for managing account tokens linked to the web app."""
    message = update.effective_message
    if not message:
        return

    await message.reply_text(token_text)


async def photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Learning how to send photo to user via bot
    """
    msg = update.effective_message

    if not msg:
        return

    b = await msg.reply_photo(
        # photo="/home/rana/Pictures/linux_logo.png",
        photo="https://avatars.githubusercontent.com/u/142967497?v=4",
    )
    print(b)
