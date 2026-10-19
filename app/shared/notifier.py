"""
app/shared/notifier.py

Website visit alerts sent to the Telegram group with python-telegram-bot.
"""

import asyncio
from collections.abc import Coroutine
from datetime import datetime
import html
from pathlib import Path
from typing import (
    Any,
    Final,
)
from zoneinfo import ZoneInfo

from fastapi import Request
from pydantic import BaseModel
from telegram.ext import ExtBot
from telegram.error import TelegramError

from app.bot_tg.application import application
from app.config import settings
from app.shared.logger_related import RanaLogger

IST = ZoneInfo("Asia/Kolkata")


# from telegram import Bot
# _bot: Bot | None = None
# def get_bot_obj_1() -> Bot:
#     """
#     Old One not use anymore
#     This is for when i want to make bot here from scratch
#     One shared Bot for the whole web process (keeps the connection pool).
#     """

#     global _bot
#     if _bot is None:
#         _bot = Bot(token=settings.bot.token.get_secret_value())
#     return _bot


def get_bot_obj() -> ExtBot[None]:
    """
    This has advace bot having many defaults
    """

    return application.bot


bot = get_bot_obj()


class HealthLog(BaseModel):
    time: int
    ip: str
    method: str
    path: str
    query: str = ""  # new: e.g. "visit=1"
    user_agent: str | None = None
    origin: str | None = None
    referer: str | None = None
    platform: str | None = None
    screen: str | None = None
    viewport: str | None = None
    dpr: str | None = None
    lang: str | None = None
    tz: str | None = None


def esc(value: str | None) -> str:
    """
    HTML-escape a value for Telegram, '-' when empty.
    """
    return html.escape(value or "-")


def build_visit_text(log: HealthLog) -> str:
    indian_time = datetime.fromtimestamp(log.time, tz=IST)
    full_path = f"{log.path}?{log.query}" if log.query else log.path

    return (
        f"🌐 <b>Website Health Check Visit</b>\n\n"
        f"🕒 <code>{indian_time:%Y-%m-%d %I:%M:%S %p} IST</code>\n"
        f"📍 <b>IP:</b> <code>{html.escape(log.ip)}</code>\n"
        f"🔗 <b>Origin:</b> {esc(log.origin)}\n"
        f"↩️ <b>Referer:</b> {esc(log.referer)}\n"
        f"🛣 <b>Request:</b> <code>{html.escape(log.method)} {html.escape(full_path)}</code>\n"
        f"📱 <b>Platform:</b> {esc(log.platform)}\n"
        f"🖥 <b>Screen:</b> {esc(log.screen)} (window {esc(log.viewport)}, ×{esc(log.dpr)})\n"
        f"🌍 <b>Language / Timezone:</b> {esc(log.lang)} / {esc(log.tz)}\n"
        f"💻 <b>Browser:</b> {esc(log.user_agent)}"
    )


def get_client_ip(request: Request) -> str:
    # X-Real-IP is set by nginx; without it you only see 127.0.0.1
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


async def notify_visit(
    full_text: str | None = None,
) -> None:
    if not settings.bot.health_check_notify_enabled:
        return

    notifier_chat_id = settings.bot.health_check_notify_chat_id

    if not notifier_chat_id:
        return

    if full_text:
        text = full_text
    else:
        print("full_text should to pass in notify visist")
        return

    try:
        await bot.send_message(
            chat_id=notifier_chat_id,
            text=text,
        )
    except TelegramError as e:
        # also covers network errors and flood limits (RetryAfter)
        print("Telegarm notificaiton not send yet.")
        RanaLogger.warning(f"Visit alert to group {notifier_chat_id} failed: {e}")


MAX_UPLOAD_BYTES: Final[int] = 49 * 1024 * 1024  # Telegram bot upload limit is 50 MB

_tasks: set[asyncio.Task[None]] = set()


def fire_and_forget(coro: Coroutine[Any, Any, None]) -> None:
    """
    Start now without waiting; keeps a reference so it is not garbage collected.
    """
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


class ClientInfo(BaseModel):
    ip: str
    user_agent: str | None = None
    origin: str | None = None
    referer: str | None = None
    platform: str | None = None
    screen: str | None = None
    viewport: str | None = None
    lang: str | None = None
    tz: str | None = None


def _cut(value: str | None, n: int) -> str | None:
    return value[:n] if value else None


def collect_client_info(
    request: Request,
    extras: dict[str, Any] | None = None,
) -> ClientInfo:
    """
    Headers come from the request; screen/lang/tz are sent by app.js in the body.
    """
    extras = extras or {}
    return ClientInfo(
        ip=get_client_ip(request),
        user_agent=_cut(request.headers.get("user-agent"), 200),
        origin=_cut(request.headers.get("origin"), 100),
        referer=_cut(request.headers.get("referer"), 100),
        platform=(request.headers.get("sec-ch-ua-platform") or "").strip('"') or None,
        screen=_cut(extras.get("screen"), 20),
        viewport=_cut(extras.get("viewport"), 20),
        lang=_cut(extras.get("lang"), 20),
        tz=_cut(extras.get("tz"), 40),
    )


def _client_lines(c: ClientInfo) -> str:
    return (
        f"📍 <b>IP:</b> <code>{html.escape(c.ip)}</code>\n"
        f"📱 <b>Platform:</b> {esc(c.platform)}\n"
        f"🖥 <b>Screen:</b> {esc(c.screen)} (window {esc(c.viewport)})\n"
        f"🌍 <b>Language / Timezone:</b> {esc(c.lang)} / {esc(c.tz)}\n"
        f"🔗 <b>Origin:</b> {esc(c.origin)}\n"
        f"💻 <b>Browser:</b> {esc(c.user_agent)}"
    )


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")


async def _send_admin_text(text: str) -> None:
    if not settings.bot.web_download_notify_enabled:
        return
    chat_id = settings.bot.health_check_notify_chat_id
    if not chat_id:
        return
    try:
        await get_bot_obj().send_message(
            chat_id=chat_id,
            text=text,
        )
    except TelegramError as e:
        RanaLogger.warning(f"Admin alert failed: {e}")


async def notify_download_attempt(client: ClientInfo, url: str, fmt: str) -> None:
    await _send_admin_text(
        "🎧 <b>Song download requested</b>\n\n"
        f"🕒 <code>{_now_ist()}</code>\n"
        f"🔗 <b>Song URL:</b> {html.escape(url[:300])}\n"
        f"🎚 <b>Format:</b> {html.escape(fmt.upper())}\n"
        f"{_client_lines(client)}"
    )


async def notify_download_failed(client: ClientInfo, url: str, error: str) -> None:
    await _send_admin_text(
        "❌ <b>Song download failed</b>\n\n"
        f"🔗 <code>{html.escape(url[:300])}</code>\n"
        f"📍 IP: <code>{html.escape(client.ip)}</code>\n"
        f"⚠️ {html.escape(error[:300])}"
    )


async def forward_song_to_group(
    client: ClientInfo,
    url: str,
    audio_path: str,  # i will later use Path obj
    title: str,
    fmt: str,
    duration_text: str,
) -> None:
    if not settings.bot.web_download_notify_enabled:
        return

    group_id = settings.bot.song_forward_group_id
    if not group_id:
        return

    try:
        audio_file = Path(audio_path)

        caption = (
            f"🎵 <b>{html.escape((title or 'Unknown')[:100])}</b>\n"
            f"🎚 {html.escape(fmt.upper())} • ⏱ {html.escape(duration_text)}\n"
            f"🔗 <code>{html.escape(url[:200])}</code>\n\n"
            "⬇️ <b>Downloaded from the website</b>\n"
            f"📍 IP: <code>{html.escape(client.ip)}</code>\n"
            f"📱 {html.escape(client.platform or '-')} • "
            f"🖥 {html.escape(client.screen or '-')} • "
            f"🌍 {html.escape(client.tz or '-')}"
        )

        if audio_file.stat().st_size > MAX_UPLOAD_BYTES:
            # TODO later due to local bot api server it will work
            await bot.send_message(
                chat_id=group_id,
                text=caption + "\n\n⚠️ File is over 50 MB, not uploaded.",
            )
            return

        with open(audio_path, "rb") as f:
            await bot.send_audio(
                chat_id=group_id,
                audio=f,
                title=(title or "")[:64],
                caption=caption,
            )
    except (TelegramError, OSError) as e:
        RanaLogger.warning(f"Song upload to group {group_id} failed: {e}")
