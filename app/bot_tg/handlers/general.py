"""
app/bot_tg/handlers/general.py

Some general things of handler will be here
"""

"""
app/bot_tg/handlers/song_link.py

Here songs link will extract from the message and then
the thigns will decide here what to do!
"""


from telegram import (
    Update,
    MessageEntity,
    # LinkPreviewOptions,
)

from telegram.ext import (
    ContextTypes,
)

from app.shared.logger_related import RanaLogger

from ..utils import extract_valid_song_link_from_message_entities


from ..ui.text_formatter import (
    generate_non_suno_link_received_text,
    generate_no_link_received_text,
)

from ..constants import StickerFileId


from .song_link import handle_suno_song_link
from .tts import handle_text_to_voice

#


async def route_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    This will take the message text and decide what to do
    """

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        RanaLogger.warning(
            "Message & Chat should present when in text",
        )
        return

    # https://docs.python-telegram-bot.org/en/stable/telegram.message.html#telegram.Message.parse_entities
    urls_dict = message.parse_entities(
        types=[
            MessageEntity.URL,
        ]
    )

    # print(f"Printing the URLS LIST {urls_dict}")

    if not urls_dict:
        text = generate_no_link_received_text()
        await message.reply_sticker(
            StickerFileId.NO_RED_SMOKE,
        )
        await message.reply_text(
            text,
        )
        await handle_text_to_voice(
            update=update,
            context=context,
            text=message.text or "No Text Found",
        )

        return

    is_valid, final_song_url = extract_valid_song_link_from_message_entities(
        urls_dict,
    )

    if not is_valid:
        txt = generate_non_suno_link_received_text(
            wrong_url=final_song_url,
        )
        await message.reply_text(txt)
        return

    await handle_suno_song_link(
        update=update,
        context=context,
        final_song_url=final_song_url,
    )
