"""
app/bot_tg/keyboards.py

The keyboards which will attach with the bot message
mostly will be created and kept here for easy access
"""

from urllib.parse import quote


from telegram import InlineKeyboardButton
from telegram.constants import KeyboardButtonStyle


from app.config import settings

#

RAZORPAY_PROFILE_LINK = settings.external.razorpay_profile_link
PAYPAL_PROFILE_LINK = settings.external.paypal_profile_link
MY_WEBSITE_LINK = settings.external.my_donation_website
SUNO_SONG_CREATE_LINK = settings.external.suno_song_create_link
MY_TELEGRAM_CONTACT_LINK = f"https://t.me/{settings.bot.help_account_username}"


UPI_Profile_Button = InlineKeyboardButton(
    "💳 Donate On UPI",
    url=RAZORPAY_PROFILE_LINK,
)

PAYPAL_Profile_Button = InlineKeyboardButton(
    "💙 Donate On PayPal",
    url=PAYPAL_PROFILE_LINK,
)


def generate_dynamic_keyboard(
    final_url: str,
    mini_app_url: str | None = None,
):
    """
    Generates the structured keyboard layout for song options:
    - Row 1: Original Song (Wide)
    - Row 2: MP3 & WAV (Split)
    - Row 3: Video Download & Open in Suno (Split)
    - Row 4: Select Song Mini App (Flask Web App integration)
    """

    keyboard = [
        [
            InlineKeyboardButton(
                "🎵 Download Original Song",
                url=MY_WEBSITE_LINK,
                style=KeyboardButtonStyle.BLUE,
            )
        ],
        [
            InlineKeyboardButton(
                "🎧 MP3 Format",
                url=MY_WEBSITE_LINK,
            ),
            InlineKeyboardButton(
                "🎼 WAV Format",
                url=MY_WEBSITE_LINK,
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Open in Suno",
                url=final_url,
            ),
            InlineKeyboardButton(
                "⭐ Buy Stars",
                url=RAZORPAY_PROFILE_LINK,
            ),
        ],
        [
            InlineKeyboardButton(
                "💝 Donate Us",
                url=RAZORPAY_PROFILE_LINK,
            ),
            InlineKeyboardButton(
                "📩 Contact Us",
                url=MY_TELEGRAM_CONTACT_LINK,
            ),
        ],
    ]

    return keyboard


def generate_buttons_for_attach_with_song(
    song_url: str | None = None,
):

    buttons: list[list[InlineKeyboardButton]] = []

    # First row
    first_row = [
        InlineKeyboardButton(
            "🎵 Create New Song",
            url=SUNO_SONG_CREATE_LINK,
        )
    ]

    buttons.append(first_row)

    if song_url:
        bot_username = (
            f"@{settings.bot.username.lstrip('@')}" if settings.bot.username else ""
        )
        share_text = (
            f"{bot_username}\n"
            f"🎵 Check out this amazing song on Suno!\n\n"
            f"⬇️ Download it easily with this bot!\n"
            f"🆓 Fast, simple & free!\n"
            f"✨ Try it now!"
        )

        share_song_url = (
            "https://t.me/share/url"
            f"?url={quote(song_url)}"
            f"&text={quote(share_text)}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    "📤 Share Song To Friends",
                    url=share_song_url,
                )
            ]
        )

    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    "⭐ Free Stars",
                    url=RAZORPAY_PROFILE_LINK,
                )
            ]
        )

    # Second row
    buttons.append(
        [
            UPI_Profile_Button,
        ]
    )
    buttons.append(
        [
            PAYPAL_Profile_Button,
        ],
    )

    # Third row
    buttons.append(
        [
            InlineKeyboardButton(
                "📩 Contact Us",
                url=MY_TELEGRAM_CONTACT_LINK,
            ),
        ]
    )

    return buttons
