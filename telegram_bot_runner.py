"""
main_for_tg_bot.py

This is the entrypoint to start the tg bot
"""

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
)


from app.bot_tg.handlers.commands.basic import (
    help_command,
    about_command,
    settings_command,
    token_command,
    photo_command,
)
from app.bot_tg.handlers.general import route_text_message
from app.bot_tg.handlers.photo import (
    photo_handler,
)
from app.bot_tg.handlers.commands.start import start_command
from app.bot_tg.application import application
from app.bot_tg.handlers.video import get_video_file_id
from app.bot_tg.handlers.audio import audio_handler
from app.bot_tg.handlers.document import handle_document_file
from app.bot_tg.merge import merge_audio_conversation_handler

#

if __name__ == "__main__":

    start_handler = CommandHandler("start", start_command)
    text_handler = MessageHandler(
        filters=filters.TEXT & (~filters.COMMAND) & filters.ChatType.PRIVATE,
        callback=route_text_message,
    )
    help_handler = CommandHandler("help", help_command)
    about_handler = CommandHandler("about", about_command)
    settings_handler = CommandHandler("settings", settings_command)
    token_handler = CommandHandler("token", token_command)
    photo_command_handler = CommandHandler("photo", photo_command)

    application.add_handler(merge_audio_conversation_handler)
    application.add_handler(start_handler)
    application.add_handler(text_handler)
    application.add_handler(help_handler)
    application.add_handler(about_handler)
    application.add_handler(settings_handler)
    application.add_handler(token_handler)
    application.add_handler(photo_command_handler)
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            get_video_file_id,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.AUDIO,
            audio_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.ATTACHMENT,
            handle_document_file,
        )
    )
    application.run_polling()
