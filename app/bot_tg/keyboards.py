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

Razorpay_Profile_Button = InlineKeyboardButton(
    "Premium Stars⭐",
    url=RAZORPAY_PROFILE_LINK,
)


def generate_dynamic_keyboard(
    song_url: str | None = None,
    final_url: str | None = None,
) -> list[list[InlineKeyboardButton]]:
    """
    Generate a complete inline keyboard for song messages.

    Layout:
    - Row 1: Download original song
    - Row 2: MP3 and WAV formats
    - Row 3: Create a new song and open in Suno
    - Row 4: Share the song
    - Row 5: Buy Stars and donate
    - Row 6: Contact support
    """

    buttons: list[list[InlineKeyboardButton]] = []

    # Row 1: Download original song
    buttons.append(
        [
            InlineKeyboardButton(
                "🎵 Download in MP3 or WAV",
                url=MY_WEBSITE_LINK,
                style=KeyboardButtonStyle.BLUE,
            )
        ]
    )

    # Row 3: Song creation and Suno
    song_buttons = [
        InlineKeyboardButton(
            "✨ Create New Song",
            url=SUNO_SONG_CREATE_LINK,
        )
    ]

    if final_url:
        song_buttons.append(
            InlineKeyboardButton(
                "🌐 Open in Suno",
                url=final_url,
            )
        )

    buttons.append(song_buttons)

    # Row 4: Share song
    if song_url:
        bot_username = (
            f"@{settings.bot.username.lstrip('@')}" if settings.bot.username else ""
        )

        share_text = (
            f"{bot_username}\n"
            "🎶 Check out this amazing song on Suno!\n\n"
            "📥 Download it easily with this bot!\n"
            "🆓 Fast, simple & free!\n"
            "🚀 Try it now!"
        )

        share_song_url = (
            "https://t.me/share/url"
            f"?url={quote(song_url)}"
            f"&text={quote(share_text)}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    "📤 Share Song with Friends",
                    url=share_song_url,
                )
            ]
        )

    # Row 5: Support the bot
    buttons.append(
        [
            InlineKeyboardButton(
                "⭐ Buy Stars",
                url=RAZORPAY_PROFILE_LINK,
            ),
            InlineKeyboardButton(
                "💝 Donate",
                url=RAZORPAY_PROFILE_LINK,
            ),
        ]
    )

    # Row 6: Contact support
    buttons.append(
        [
            InlineKeyboardButton(
                "📩 Contact Us / Increase Speed",
                url=MY_TELEGRAM_CONTACT_LINK,
            )
        ]
    )

    return buttons
