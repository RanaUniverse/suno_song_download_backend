"""
app/bot_tg/config.py

Bot related configurations settings will be here
"""

from enum import Enum, StrEnum


class MessageEffectEmojies(Enum):
    """
    This class content will have some content which help
    to send the user some message with some animations so that it will looks good...
    Some Values are as:
    LIKE = 👍
    DISLIKE = 👎
    HEART = ❤️
    FLAME = 🔥
    TADA = 🎉
    POO = 💩
    """

    LIKE = "5107584321108051014"
    DISLIKE = "5104858069142078462"
    HEART = "5159385139981059251"
    FLAME = "5104841245755180586"
    TADA = "5046509860389126442"
    POO = "5046589136895476101"


class StickerFileId(StrEnum):
    LOADING_ROUNDED = (
        "CAACAgUAAxkBAAPaar4hDRS87kg9MPV5RpHtg4RuDQUAAtYiAAIVrvFVMtv6jqApWB09BA"
    )

    SAND_CLOCK_WAITING = (
        "CAACAgUAAxkBAAPbar4hFEh0EzYKNqkJjoMGBo9y67kAAnQnAALSR_lVOCS06VojPrI9BA"
    )

    UPLOADING_CLOUD = (
        "CAACAgUAAxkBAAPcar4hFmbSjfbK02LPKoDHttAIJgEAAkEiAAKP1_FVaMhlLqfPyQABPQQ"
    )

    LIGHTNING = "CAACAgUAAxkBAAPdar4hGNn8H9orXcCdLP7_diN3G-gAArEhAAInY_BVlF94BW0xVok9BA"

    GREEN_TICK = (
        "CAACAgUAAxkBAAPiar4hf2-rKy1w2EpijaRrKdFu-ZwAAqglAAJAlvBViwf255ziDSA9BA"
    )

    NO_RED_SMOKE = (
        "CAACAgUAAxkBAAPjar4hgJOt0g5woPX7wQABFhfaC5xMAAIxHQAC4m3wVfbqWGQTILYGPQQ"
    )
