"""
app/shared/notifier.py

Website visit alerts sent to the Telegram group with python-telegram-bot.
"""

import html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from fastapi import Request
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import settings
from app.shared.logger_related import RanaLogger

_bot: Bot | None = None
IST = ZoneInfo("Asia/Kolkata")


class HealthLog(BaseModel):
    time: int
    ip: str
    method: str
    path: str
    query: str = ""  # new: e.g. "visit=1"
    user_agent: str | None = None
    origin: str | None = None
    referer: str | None = None


def build_visit_text(log: HealthLog) -> str:
    indian_time = datetime.fromtimestamp(log.time, tz=IST)
    full_path = f"{log.path}?{log.query}" if log.query else log.path

    return (
        f"🌐 <b>Website Health Check Visit</b>\n\n"
        f"🕒 <code>{indian_time:%Y-%m-%d %I:%M:%S %p} IST</code>\n"
        f"📍 <b>IP:</b> <code>{html.escape(log.ip)}</code>\n"
        f"🔗 <b>Origin:</b> {html.escape(log.origin or '-')}\n"
        f"↩️ <b>Referer:</b> {html.escape(log.referer or '-')}\n"
        f"🛣 <b>Request:</b> <code>{html.escape(log.method)} {html.escape(full_path)}</code>\n"
        f"💻 <b>Browser:</b> {html.escape(log.user_agent or '-')}"
    )


async def _get_bot() -> Bot:
    """
    One shared Bot for the whole web process (keeps the connection pool).
    """

    global _bot
    if _bot is None:
        bot = Bot(token=settings.bot.token.get_secret_value())
        await bot.initialize()
        _bot = bot
    return _bot


async def close_bot() -> None:
    global _bot
    if _bot is not None:
        await _bot.shutdown()
        _bot = None


def get_client_ip(request: Request) -> str:
    # X-Real-IP is set by nginx; without it you only see 127.0.0.1
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


async def notify_visit(
    full_text: str | None = None,
    ip: str = "",
    origin: str | None = None,
    user_agent: str | None = None,
) -> None:
    if not settings.bot.health_check_notify_enabled:
        return

    notifier_chat_id = settings.bot.health_check_notify_chat_id

    if not notifier_chat_id:
        return

    if full_text:
        text = full_text
    else:
        text = (
            "🌐 <b>Website visit</b>\n"
            f"🕒 {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC\n"
            f"📍 IP: <code>{html.escape(ip)}</code>\n"
            f"🔗 Origin: {html.escape(origin or '-')}\n"
            f"💻 {html.escape(user_agent or '-')}"
        )

    try:
        bot = await _get_bot()
        await bot.send_message(
            chat_id=notifier_chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        # also covers network errors and flood limits (RetryAfter)
        print("Telegarm notificaiton not send yet.")
        RanaLogger.warning(f"Visit alert to group {notifier_chat_id} failed: {e}")
