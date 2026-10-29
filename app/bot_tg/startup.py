"""
app/bot_tg/startup.py

This will say what will happens on the startup of the bot
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.ext import Application

from app.config import settings
from app.shared.logger_related import RanaLogger

#


async def notify_admin_on_startup(
    application: Application,  # type: ignore #TODO
    # type: ignore #TODO
) -> None:
    local_api = settings.bot.local_api

    if local_api.enabled:
        api_mode = "Local Bot API"
        api_server = local_api.server_url
    else:
        api_mode = "Official Telegram Bot API"
        api_server = "https://api.telegram.org"

    local_mode = "Enabled" if local_api.enabled and local_api.local_mode else "Disabled"

    startup_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
        "%Y-%m-%d %H:%M:%S IST"
    )

    message = (
        "🚀 <b>Telegram Bot Started...</b>\n\n"
        f"<b>Owner:</b> {settings.owner_name}\n"
        f"<b>Startup time:</b> {startup_time}\n"
        f"<b>Bot API mode:</b> {api_mode}\n"
        f"<b>Local API server:</b> {api_server}\n"
        f"<b>Local mode:</b> {local_mode}\n"
        "<b>Polling:</b> About to start\n"
    )
    if settings.bot.startup_notify_enabled and settings.bot.admin_chat_id:
        RanaLogger.info(message)
        await application.bot.send_message(  # type: ignore #TODO
            # it need applicaiton problem solve
            chat_id=settings.bot.admin_chat_id,
            text=message,
        )
    else:
        RanaLogger.info("Startup Notification is not Set Yet...")
        RanaLogger.info(message)
