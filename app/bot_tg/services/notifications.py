"""
app/bot_tg/services/notifications.py
"""

from collections.abc import Awaitable, Callable


from telegram import Bot, LinkPreviewOptions, User
from telegram.error import TelegramError


from app.config import settings
from app.features.suno.models import SongInfo
from app.shared.logger_related import RanaLogger


from ..utils import escape_html
from ..ui.text_formatter import generate_song_details_only

#


ChatId = int | str


async def _deliver(
    send: Callable[[ChatId], Awaitable[object]],
    event: str,
) -> bool:
    """
    Look up the admin chat, run `send(chat_id)`,
    and handle errors in one place.
    """

    chat_id = settings.bot.notification_chat_id


    if not chat_id:
        RanaLogger.warning(f"Notification '{event}' skipped: no chat configured.")
        return False

    try:
        await send(chat_id)
        return True

    except TelegramError as e:
        RanaLogger.warning(f"Notification '{event}' failed: {e}")
        return False


async def notify_new_user(
    bot: Bot,
    user: User,
) -> bool:

    safe_name = escape_html(user.full_name)

    text = (
        "👤 <b>New User Started the Bot</b>\n\n"
        f"👤 <b>Name:</b>\n"
        f'<a href="tg://user?id={user.id}">{safe_name}</a>\n'
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"<b>Username:</b>-> {user.username}"
    )
    return await _deliver(
        lambda chat_id: bot.send_message(
            chat_id=chat_id,
            text=text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        ),
        event="new_user",
    )


async def notify_song_downloaded(
    bot: Bot,
    audio_file_id: str,
    user_name: str,
    song: SongInfo,
) -> bool:
    caption = (
        f"🎵 <b>Song downloaded by:</b> {user_name}\n\n"
        f"{generate_song_details_only(song)}"
    )

    return await _deliver(
        lambda chat_id: bot.send_audio(
            chat_id=chat_id,
            audio=audio_file_id,
            caption=caption,
        ),
        "song_downloaded",
    )


async def notify_song_merge_done(
    bot: Bot,
    audio_file_id: str,
    user_name: str,
    merged_count: int,
) -> bool:
    caption = (
        "This song has been merged by "
        f"{user_name} and have been songs count of: {merged_count}"
    )
    return await _deliver(
        lambda chat_id: bot.send_audio(
            chat_id=chat_id,
            audio=audio_file_id,
            caption=caption,
        ),
        "merge_done",
    )
