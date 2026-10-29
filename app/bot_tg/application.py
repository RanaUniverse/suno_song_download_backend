"""
app/bot_tg/application.py

Here this will make the application object for this bot
This application object will call in the main to run the bot there
"""

from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, Defaults
from telegram.request import HTTPXRequest


from app.config import settings
from app.bot_tg.startup import notify_admin_on_startup  # type: ignore

#

BOT_TOKEN = settings.bot.token.get_secret_value()
local_api = settings.bot.local_api

my_defaults = Defaults(
    parse_mode=ParseMode.HTML,
)

request = HTTPXRequest(
    connection_pool_size=50,
    read_timeout=30,
    write_timeout=30,
    connect_timeout=30,
    pool_timeout=30,
    media_write_timeout=300,
)


builder = (
    ApplicationBuilder()
    .defaults(
        defaults=my_defaults,
    )
    .token(
        token=BOT_TOKEN,
    )
    .request(request)
    .concurrent_updates(
        concurrent_updates=10,
    )
    .post_init(  # type: ignore #TODO
        notify_admin_on_startup,
    )
)

if local_api.enabled:
    builder = (
        builder.base_url(local_api.base_url)
        .base_file_url(local_api.base_file_url)
        .local_mode(True)
    )

application = builder.build()
