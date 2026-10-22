"""
app/bot_tg/handlers.py

Some of the handlers will be kept here
"""

import asyncio
import html
from pathlib import Path


from telegram import (
    Update,
    MessageEntity,
    # LinkPreviewOptions,
    InlineKeyboardMarkup,
)
from telegram.constants import (
    ChatAction,
)
from telegram.error import (
    BadRequest,
    TelegramError,
)

from telegram.ext import (
    ContextTypes,
)

from app.config import settings
from app.shared.logger_related import RanaLogger

from .utils import extract_valid_song_link_from_message_entities

from app.features.suno_downloader import SunoScraper
from app.features.suno.models import SongInfo
from app.shared.song_info import (
    calculate_song_cost,
)

from .text_formatter import (
    generate_successful_song_caption,
    generate_non_suno_link_received_text,
    generate_wrong_suno_link_received_text,
    generate_no_link_received_text,
    generate_song_details_only,
)

from .keyboards import (
    generate_dynamic_keyboard,
)

from .config import StickerFileId


from app.config import settings

from app.features.suno.service import download_suno_song

from .thumbnail import get_audio_thumbnail

# #


BOT_TOKEN = settings.bot.token.get_secret_value()
SONG_FORWARD_GROUP_ID = settings.bot.song_forward_group_id


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This will send the later part of the command return in upper text
    '/caps this text will go to uppercase'
    """
    if not update.effective_user:
        return

    if not context.args:
        warning_text = (
            "⚠️ <b>Oops!</b> You forgot to add some text.\n\n"
            "Please use words after the /caps command like this:\n"
            "<code>/caps hello world</code> 🔠"
        )
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=warning_text,
        )
        return

    uppercased_text = " ".join(context.args).upper()

    response_text = f"🔠 <b>Your Uppercased Text:</b>\n\n\n{uppercased_text}"
    await context.bot.send_message(
        update.effective_user.id,
        response_text,
    )


async def get_url_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This will try to extract the url from the text and send user back.

    From the user text, i want it will extract the first url and then try
    to match this with my base_url ie target_url
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
    urls_dict = message.parse_entities(types=[MessageEntity.URL])

    print(f"Printing the URLS LIST {urls_dict}")

    if not urls_dict:
        text = generate_no_link_received_text()
        await message.reply_sticker(
            StickerFileId.NO_RED_SMOKE,
        )
        await message.reply_text(
            text,
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

    fetch_task = asyncio.create_task(
        asyncio.to_thread(
            SunoScraper().scrape_song_info,
            final_song_url,
        )
    )

    lightning_sticker = await message.reply_sticker(
        StickerFileId.LIGHTNING,
    )

    # await message.reply_chat_action(
    #     action=ChatAction.UPLOAD_PHOTO,
    # )
    try:
        song_data: SongInfo = await fetch_task

    except Exception as e:
        RanaLogger.error(f"Error scraping song: {e}")
        await lightning_sticker.delete()
        await message.reply_text(
            f"Timeout To Get The song\n" + generate_wrong_suno_link_received_text(),
            do_quote=True,
        )
        return

    RanaLogger.info(
        f"Basic Song Data Requested by, {chat.id}:-> {song_data}",
    )

    star_cost = calculate_song_cost(
        song_info=song_data,
    )

    caption = generate_successful_song_caption(
        song_info=song_data,
        star_cost=star_cost,
    )

    # Here i need to check if user has valid star in his wallet
    # i will impliment these features later

    try:
        buttons = generate_dynamic_keyboard(final_song_url)
        await message.reply_photo(
            photo=song_data.image_url or "",
            # TODO i need to htink how to handle image if not
            caption=caption,
            do_quote=True,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        loading_sticker = await message.reply_sticker(
            StickerFileId.LOADING_ROUNDED,
        )
        await lightning_sticker.delete()

        song_path_after_download = await asyncio.to_thread(
            download_suno_song,
            song_data,
        )

        uploading_sticker = await message.reply_sticker(
            StickerFileId.UPLOADING_CLOUD,
        )

        await loading_sticker.delete()

        if song_path_after_download is not None:
            # TODO
            audio_path = Path(song_path_after_download)

            with open(song_path_after_download, "rb") as file:
                await message.reply_chat_action(
                    action=ChatAction.UPLOAD_VOICE,
                )
                try:
                    song_caption = None
                    if settings.bot.show_song_caption:
                        song_caption = (
                            f"🎵✨ Enjoy Your Song!\n\n"
                            f"🌐 https://SunoAisongDownload.Online\n"
                            f"📥 Download Any Suno Song Instantly!\n"
                            f"💡 For the Best Experience, Open Our Website in Google Chrome 🚀"
                        )
                    audio_after_send = await message.reply_audio(
                        audio=file,
                        duration=song_data.duration_in_seconds,
                        # filename="I will not pass because this is will generate automatically",
                        # performer="Rana Universe Performer",
                        # title="Rana Universe Track Title",
                        caption=song_caption,
                        thumbnail=get_audio_thumbnail(audio_path),
                        do_quote=True,
                    )

                    if audio_after_send.audio:
                        print(audio_after_send)

                        user_mention = (
                            f'<a href="tg://user?id={user.id}">'
                            f"{html.escape(user.full_name)}</a>"
                        )
                        await forward_song_to_channel(
                            context=context,
                            audio_file_id=audio_after_send.audio.file_id,
                            song_data=song_data,
                            user_name=f"{user_mention}",
                        )

                except Exception as e:
                    await message.reply_text(
                        f"Sending Audio Got TimeOUT, Please Contact Admin",
                    )
                    RanaLogger.info(f"{e}")
                    return ()

        else:
            # this parts means the song path is none, ie not exists
            await message.reply_text(
                "❌ <b>Audio Download Failed</b>\n\n"
                "😔 I couldn't download the audio for this song right now.\n\n"
                "🔄 <b>Please try again in a few moments.</b>\n"
                "💡 If the problem continues, you can contact the admins for help. 🆘",
                do_quote=True,
            )

        await uploading_sticker.delete()

    except BadRequest as e:
        RanaLogger.warning(
            f"❌ Telegram could not send the image: {e}",
        )

        await message.reply_text(
            "❌ <b>Couldn't Process This Song</b>\n\n"
            "It looks like this link is <b>invalid, unavailable, "
            "or no longer accessible</b>.\n\n"
            "🔗 Please send a valid <b>Suno song URL</b> and try again.\n\n"
            "🎵 <i>Send the song link again to continue.</i>",
            do_quote=True,
        )

    except TelegramError as e:
        RanaLogger.warning(
            f"❌ Telegram error while sending photo: {e}",
        )

        await message.reply_text(
            caption,
            do_quote=True,
        )


async def forward_song_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    audio_file_id: str,
    song_data: SongInfo,
    user_name: str,
) -> bool:
    """
    Forward an already-uploaded Telegram audio file to the configured
    song channel.

    Returns:
        True: song was successfully sent
        False: forwarding was skipped or failed
    """

    # Forwarding is disabled/not configured
    if not SONG_FORWARD_GROUP_ID:
        RanaLogger.info("Song forwarding is disabled: no channel ID configured.")
        return False

    try:
        await context.bot.send_audio(
            chat_id=SONG_FORWARD_GROUP_ID,
            audio=audio_file_id,
            caption=(
                f"🎵 <b>Song downloaded by:</b> {user_name}\n\n"
                f"{generate_song_details_only(song_data)}\n"
            ),
        )

        RanaLogger.info(
            f"Song successfully forwarded to channel. "
            f"channel_id={SONG_FORWARD_GROUP_ID}, "
            f"file_id={audio_file_id}"
        )

        return True

    except TelegramError as e:
        RanaLogger.warning(
            f"Failed to forward song to channel " f"{SONG_FORWARD_GROUP_ID}: {e}"
        )
        return False
