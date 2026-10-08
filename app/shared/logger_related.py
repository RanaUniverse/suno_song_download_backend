"""
app/logger_related.py

Here i will use logger_related code which i will import
in other places to use
"""

import logging
from pathlib import Path

from app.config import settings

# This Below logging i copy paste from teh PTB docs,
# This are used by ptb backend so i dont think to touch this below

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Avoid too much logging from `httpx`
logging.getLogger("httpx").setLevel(logging.WARNING)

# General logger (backend use) so in the main.py i need to import this logger.
logger = logging.getLogger(__name__)


# Below Logics are for making the log for my own beheaviour
# which includes use the my log file name from bot_config_settings module

LOG_FILE_NAME = settings.data_path.log_filename
DATA_FOLDER_NAME = settings.data_path.data_foldername

LOG_FILE_PATH = Path.cwd() / DATA_FOLDER_NAME / LOG_FILE_NAME

# 🌟 2️⃣ Custom `RanaLogger` for file logging i will think to use.

LOG_FILE_PATH.parent.mkdir(exist_ok=True)

# from logging.handlers import RotatingFileHandler
# # Use RotatingFileHandler to manage log size & recreation
# file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2)


RanaLogger = logging.getLogger("Rana Name")
RanaLogger.setLevel(logging.INFO)

file_handler = logging.FileHandler(
    filename=LOG_FILE_PATH,
)

file_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    ),
)

RanaLogger.addHandler(file_handler)
