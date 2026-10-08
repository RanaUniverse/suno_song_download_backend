"""
app/bot_tg/application.py

Here this will make the application object for this bot
This application object will call in the main to run the bot there
"""

from telegram.ext import ApplicationBuilder, Defaults
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest


from app.config import settings

#

BOT_TOKEN = settings.bot.token.get_secret_value()

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


application = (
    ApplicationBuilder()
    .token(
        token=BOT_TOKEN,
    )
    .defaults(
        defaults=my_defaults,
    )
    .request(request)
    .concurrent_updates(
        concurrent_updates=10,
    )
    .build()
)
