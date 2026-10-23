"""
app/bot_tg/merge.py

Audio merge conversation.

Flow:
    /merge or /merge_audio or /m -> bot asks for audio files (all of the same type)
    user sends audio             -> bot replies with that audio's duration (from Telegram)
    /merge_now                   -> download all songs (progress message is edited),
                                    merge with ffmpeg, show the result info
    /cancel                      -> stop and clear everything

Audio that has no duration from Telegram (sent as a document/file, voice,
or duration == 0) is rejected with a quoted reply.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta, datetime
import html
from pathlib import Path
import re
import shutil

from telegram import (
    Audio,
    Bot,
    Message,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


import imageio_ffmpeg  # type: ignore


from app.config import settings
from app.shared.logger_related import RanaLogger

from .audio import format_duration

#

FFMPEG_EXE: str = imageio_ffmpeg.get_ffmpeg_exe()

COLLECTING = 0

MIN_FILES_TO_MERGE = settings.audio_merge.min_files
MAX_FILES_TO_MERGE = settings.audio_merge.max_files

MERGE_WORK_DIR = settings.audio_merge.work_dir


# Keys used inside context.user_data
KEY_FILES = "merge_files"  # list[MergeItem]
KEY_MIME = "merge_mime"  # mime type of the first accepted audio

UNSUPPORTED_TEXT = (
    "❌ <b>This file is not supported here.</b>\n"
    "Telegram did not give me the duration of this file, so I can't "
    "add it to the merge.\n\n"
    "Please use this bot to download the songs first "
    "and then merge them, or use the <b>premium features</b>."
    "Please Don't Send This Type of File Next Time\n"
    "Only Send the songs which has duration in the telegram app."
)

# ffmpeg encoder settings by OUTPUT extension.
# Suno ".m4a" files are really Opus inside an MP4 container, and the m4a
# muxer cannot hold Opus with "-c copy", so we re-encode to AAC.
ENCODER_ARGS: dict[str, list[str]] = {
    ".m4a": ["-c:a", "aac", "-b:a", "192k"],
    ".mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
    ".wav": ["-c:a", "pcm_s16le"],
}

DownloadedCallback = Callable[[int, int, "MergeItem"], Awaitable[None]]
MergingCallback = Callable[[], Awaitable[None]]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def merge_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔀 Merge Audio Now",
                    callback_data="merge_now",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel Now",
                    callback_data="merge_cancel",
                ),
            ],
        ]
    )


@dataclass(frozen=True, slots=True)
class MergeItem:
    file_id: str
    file_name: str
    duration: int


def to_seconds(duration: int | timedelta | None) -> int:
    """
    PTB can give int or timedelta depending on version/config.
    """
    if duration is None:
        return 0
    if isinstance(duration, timedelta):
        return int(duration.total_seconds())
    return int(duration)


def format_size(size: int | None) -> str:
    if size is None:
        return "Unknown"
    return f"{size / (1024 * 1024):.2f} MB"


def get_files(context: ContextTypes.DEFAULT_TYPE) -> list[MergeItem]:
    if context.user_data is None:
        raise RuntimeWarning("Context should be present")
    return context.user_data.setdefault(KEY_FILES, [])


def clear_merge_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data is None:
        return None

    context.user_data.pop(KEY_FILES, None)
    context.user_data.pop(KEY_MIME, None)


def audio_to_item(audio: Audio) -> MergeItem:
    """
    Keep only what we need later for downloading + merging.
    """
    return MergeItem(
        file_id=audio.file_id,
        file_name=audio.file_name or audio.file_unique_id,
        duration=to_seconds(audio.duration),
    )


async def safe_edit(message: Message, text: str) -> None:
    """
    Edit a message, ignore harmless errors (like 'message is not modified').
    """
    try:
        await message.edit_text(text)
    except BadRequest as error:
        if "not modified" not in str(error).lower():
            RanaLogger.info(f"merge: edit_text failed: {error}")


# ---------------------------------------------------------------------------
# Conversation handlers
# ---------------------------------------------------------------------------


async def merge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point:
    /merge or /merge_audio or /m
    or Sending A Audio File to the Bot
    """
    message = update.effective_message
    if message is None:
        return ConversationHandler.END

    if not settings.audio_merge.enabled:
        await message.reply_text(
            text="🚫 🎵 Audio merging is currently disabled. Please try again later.",
        )
        return ConversationHandler.END

    clear_merge_data(context)  # always start fresh
    method_text = (
        "🎶 <b>Audio Merge</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the songs you want to merge, one by one.\n"
        "⚠️ All songs must be the <b>same type</b> "
        "(all <code>m4a</code>, or all <code>mp3</code>, or all <code>wav</code>).\n\n"
        "Send them as <b>Telegram audio</b> (not as a file/document).\n\n"
        "When you are done send /merge_now\n"
        "To stop send /cancel"
    )
    if message.audio is not None:
        # Automatically started by the user's first audio.
        await message.reply_text(method_text)

        return await receive_audio(update, context)

    # Normal /merge command flow.
    await message.reply_text(method_text)
    return COLLECTING


async def receive_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    User sent a Telegram audio while collecting.
    """
    message = update.effective_message
    if message is None or message.audio is None:
        return COLLECTING
    if context.user_data is None:
        return COLLECTING

    audio = message.audio
    files = get_files(context)
    duration = to_seconds(audio.duration)

    # 1) duration missing -> not supported
    if duration <= 0:
        await message.reply_text(
            UNSUPPORTED_TEXT,
            do_quote=True,
        )
        return COLLECTING

    # 2) same type check (compare mime type of the first accepted song)
    first_mime = context.user_data.get(KEY_MIME)
    if first_mime is not None and audio.mime_type != first_mime:
        await message.reply_text(
            "❌ <b>Different audio type.</b>\n"
            f"Your first song is <code>{html.escape(str(first_mime))}</code> but "
            f"this one is <code>{html.escape(str(audio.mime_type))}</code>.\n"
            "Please send only the same type.",
            do_quote=True,
        )
        return COLLECTING

    # 3) duplicate check
    # for now i will allow to merge same songs again and again

    # 4) limit
    if len(files) >= MAX_FILES_TO_MERGE:
        await message.reply_text(
            f"⚠️ Maximum {MAX_FILES_TO_MERGE} songs allowed. Send /merge_now",
            do_quote=True,
        )
        return COLLECTING

    # 5) accept
    # NOTE: no `await` between the checks above and this append, so with
    # concurrent_updates the order of an album is kept.
    if first_mime is None:
        context.user_data[KEY_MIME] = audio.mime_type

    files.append(audio_to_item(audio))
    count = len(files)
    running_total = sum(f.duration for f in files)
    name = files[-1].file_name

    await message.reply_text(
        f"✅ <b>Added #{count}</b>\n"
        f"├ <b>Name:</b> {html.escape(name)}\n"
        f"├ <b>Type:</b> <code>{html.escape(str(audio.mime_type))}</code>\n"
        f"├ <b>Duration:</b> {format_duration(duration)}\n"
        f"├ <b>Size:</b> {format_size(audio.file_size)}\n"
        f"└ <b>Total so far:</b> {format_duration(running_total)} "
        f"({count} songs)\n\n"
        "Send more songs, or /merge_now when finished.",
        do_quote=True,
        reply_markup=merge_keyboard(),
    )
    # `count` is saved before the await above, so the log shows the real number
    RanaLogger.info(
        f"merge: added file_id={audio.file_id} chat_id={message.chat_id} "
        f"count={count}"
    )
    return COLLECTING


async def receive_unsupported(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Document / voice / video sent while collecting: no reliable duration.
    """
    message = update.effective_message
    if message is None:
        return COLLECTING

    await message.reply_text(
        UNSUPPORTED_TEXT,
        do_quote=True,
    )
    return COLLECTING


async def receive_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Plain text etc. while collecting.
    """
    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Please send an audio file, or /merge_now to finish, /cancel to stop.",
            do_quote=True,
        )
    return COLLECTING


async def merge_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /merge_now : download all songs (with progress), merge, show result.
    """
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return ConversationHandler.END

    files = list(get_files(context))  # snapshot
    query = update.callback_query
    if query is not None:
        await query.answer("Starting Audio Merge...")
        # Delete the message containing the Merge button.
        # if isinstance(query.message, Message):
        #     try:
        #         await query.message.delete()
        #     except BadRequest as error:
        #         RanaLogger.info(
        #             f"merge: could not delete button message: {error}"
        #         )
    if len(files) < MIN_FILES_TO_MERGE:
        await message.reply_text(
            f"⚠️ Send at least {MIN_FILES_TO_MERGE} songs first "
            f"(you have {len(files)}).",
        )
        return COLLECTING

    clear_merge_data(context)

    total_seconds = sum(f.duration for f in files)
    total_count = len(files)

    status = await message.reply_text(
        f"⏳ Starting download of {total_count} songs...",
    )

    downloaded_lines: list[str] = []

    async def on_downloaded(
        index: int,
        total: int,
        item: MergeItem,
    ) -> None:
        downloaded_lines.append(f"✅ {index}. {html.escape(item.file_name)}\n")
        header = (
            f"📥 <b>Downloading songs</b> ({index}/{total})"
            if index < total
            else f"📥 <b>All {total} songs downloaded</b>"
        )
        await safe_edit(status, header + "\n\n" + "\n".join(downloaded_lines))

    async def on_merging() -> None:
        await safe_edit(
            status,
            "🔀 <b>Merging now...</b>\n"
            "This will take a little time, please wait.\n\n"
            + "\n".join(downloaded_lines),
        )

    try:
        output_path = await download_and_merge(
            bot=context.bot,
            items=files,
            chat_id=message.chat_id,
            on_downloaded=on_downloaded,
            on_merging=on_merging,
        )
        merged_seconds = await probe_duration(output_path)
    except Exception:
        RanaLogger.exception(f"merge failed for chat_id={message.chat_id}")
        await safe_edit(
            status,
            "❌ <b>Merge failed.</b>\nSomething went wrong, please try again.",
        )
        return ConversationHandler.END

    merged_text = format_duration(int(merged_seconds)) if merged_seconds else "Unknown"
    await safe_edit(
        status,
        "✅ <b>Merge finished!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"├ <b>Songs merged:</b> {total_count}\n"
        f"├ <b>Expected time (Telegram):</b> {format_duration(total_seconds)}\n"
        f"├ <b>Merged file time (ffprobe):</b> {merged_text}\n"
        f"├ <b>Size:</b> {format_size(output_path.stat().st_size)}\n"
        f"└ <b>Saved at:</b> <code>{html.escape(str(output_path))}</code>",
    )

    # ---- LATER: send the merged song to the user ------------------------
    await context.bot.send_message(
        chat_id=user.id,
        text="Your Songs is Uploading Now...",
    )
    with output_path.open("rb") as f:
        await message.reply_audio(audio=f, duration=total_seconds)
    # ----------------------------------------------------------------------

    return ConversationHandler.END


async def merge_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    /cancel : forget everything.
    """
    message = update.effective_message
    query = update.callback_query
    if query is not None:
        await query.answer("Canceling Your Request...")

    clear_merge_data(context)
    if message is not None:
        await message.reply_text(
            "🛑 Merge cancelled. Your songs list is cleared.",
        )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Download + ffmpeg merge
# ---------------------------------------------------------------------------


async def download_audio_files(
    bot: Bot,
    items: list[MergeItem],
    work_dir: Path,
    on_downloaded: DownloadedCallback | None = None,
) -> list[Path]:
    """
    Download every file_id into work_dir, keeping the order the user sent.
    With a local Bot API server (local_mode=True) get_file() already points to
    a path on disk, download_to_drive just copies it, so big files are fine.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    total = len(items)

    for index, item in enumerate(items, start=1):
        tg_file = await bot.get_file(item.file_id)
        suffix = (
            Path(item.file_name).suffix
            or Path(tg_file.file_path or "").suffix
            or ".m4a"
        )
        target = work_dir / f"{index:03}{suffix}"  # 001.m4a, 002.m4a ...
        await tg_file.download_to_drive(custom_path=target)
        paths.append(target)

        if on_downloaded is not None:
            await on_downloaded(index, total, item)

    return paths


async def merge_with_ffmpeg(paths: list[Path], output_path: Path) -> Path:
    """
    Merge files with the ffmpeg concat FILTER and re-encode.

    Why not "-f concat -c copy": the Suno .m4a files hold Opus, and Opus can't be
    copied into an .m4a container. The concat filter also works when the files
    have different sample rate / channels, because we resample each input first.
    """
    encoder = ENCODER_ARGS.get(output_path.suffix.lower())
    if encoder is None:
        raise ValueError(f"Unsupported output type: {output_path.suffix}")

    count = len(paths)
    prepare = [
        f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo[a{i}]"
        for i in range(count)
    ]
    joined = "".join(f"[a{i}]" for i in range(count))
    filter_complex = ";".join(prepare) + f";{joined}concat=n={count}:v=0:a=1[out]"

    command = [
        FFMPEG_EXE,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
    ]
    for path in paths:
        command += ["-i", str(path)]
    command += ["-filter_complex", filter_complex, "-map", "[out]", *encoder]
    command.append(str(output_path))

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode(errors='ignore')[-800:]}")

    return output_path


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


async def probe_duration(path: Path) -> float:
    process = await asyncio.create_subprocess_exec(
        FFMPEG_EXE,
        "-hide_banner",
        "-i",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    match = _DURATION_RE.search(stderr.decode(errors="ignore"))
    if not match:
        raise RuntimeError(f"Could not read duration of {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


async def download_and_merge(
    bot: Bot,
    items: list[MergeItem],
    chat_id: int,
    on_downloaded: DownloadedCallback | None = None,
    on_merging: MergingCallback | None = None,
) -> Path:
    """
    Download -> merge -> return the merged file path. Cleans temp inputs.
    """
    work_dir = MERGE_WORK_DIR / str(chat_id)
    if work_dir.exists():
        shutil.rmtree(work_dir)

    paths = await download_audio_files(bot, items, work_dir, on_downloaded)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = work_dir / f"merged_songs_{timestamp}{paths[0].suffix}"

    if on_merging is not None:
        await on_merging()

    try:
        return await merge_with_ffmpeg(paths, output_path)
    finally:
        for p in paths:
            p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Build + register
# ---------------------------------------------------------------------------


merge_audio_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            [
                "m",
                "merge",
                "merge_audio",
                "merge_song",
                "merge_songs",
            ],
            merge_start,
        ),
        MessageHandler(
            filters.AUDIO,
            merge_start,
        ),
    ],
    states={
        COLLECTING: [
            MessageHandler(
                filters.AUDIO,
                receive_audio,
            ),
            CommandHandler(
                "merge_now",
                merge_now,
            ),
            MessageHandler(
                filters.Document.ALL
                | filters.VOICE
                | filters.VIDEO
                | filters.VIDEO_NOTE,
                receive_unsupported,
            ),
            MessageHandler(
                ~filters.COMMAND,
                receive_other,
            ),
            CallbackQueryHandler(
                merge_now,
                pattern=r"^merge_now$",
            ),
            CallbackQueryHandler(
                merge_cancel,
                pattern=r"^merge_cancel$",
            ),
        ],
    },
    fallbacks=[
        CommandHandler(
            "cancel",
            merge_cancel,
        )
    ],
)
