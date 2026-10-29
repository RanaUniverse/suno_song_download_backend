"""
app/bot_tg/text_formatter.py

This will defines what the formatter will be here
This will format the text there which will use to send to users
"""

from html import escape


from app.config import settings
from app.features.suno.models import SongInfo
from app.shared.utils import get_random_demo_songs_links

#

SUNO_TARGET_DOMAIN = settings.external.suno_target_domain


def get_welcome_message(full_name: str) -> str:

    random_songs = get_random_demo_songs_links(3)
    links_formatted = "\n".join([f"🎵 <code>{link}</code>" for link in random_songs])

    startup_message = (
        f"👋 Hey <b>{escape(full_name)}</b>! Welcome To Our Bot! 🎉\n\n"
        "📥 <b>HOW TO DOWNLOAD A SONG?</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 <b>WE'RE BACK — BETTER THAN EVER!</b> 🔥\n\n"
        "⚡ <b>Ultra-Fast Downloads</b>\n"
        "👑 <b>Premium Users:</b> Ultra-fast downloads in 10 Seconds"
        "🎧 <b>Unlimited Suno Song Downloads</b>\n"
        "💬 <b>24×7 Customer Support</b>\n"
        "🎶 <b>Simple, Fast & Easy to Use</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Already have a Suno link?</b>\n"
        "Just send song link here, and let the bot handle the rest! 🎵\n\n"
        "🤔 <b>Don't have a song link?</b>\n"
        "No worries! 😎 Copy any demo song link below and send it "
        "to the bot to start your download! 👇\n\n"
        f"{links_formatted}\n\n"
        "🔥 Join our Official Channel For Updates: @HindiDJSong\n\n"
        "🚀 <b>SEND A SUNO LINK NOW AND LET THE MUSIC PLAY!</b> 🎧✨\n"
        "<b>Watch This Video Below For More Information 👇👇👇</b>"
    )

    return startup_message


help_text = (
    "🤖 <b>Help Center - Suno Song Downloader</b> 🎵\n\n"
    "Here is how you can use this bot:\n"
    "1️⃣ Copy a song link from our web platform (<code>sunoaisongdownload.online</code>).\n"
    "2️⃣ Paste and send the link directly here in the chat.\n"
    "3️⃣ The bot will validate the link and prepare your song for download! ✨\n\n"
    "<b>Need more assistance?</b> Contact our support or check out /about."
)

about_text = (
    "ℹ️ <b>About This Project</b> 🚀\n\n"
    "This Telegram bot is the companion tool for our <b>Suno Song Download Web App</b>! 🎶\n\n"
    "Built with Python, Linux Ubuntu, and powered by <code>python-telegram-bot</code>, "
    "it bridges our web platform directly to your Telegram chat for fast and easy song management. 🐧💻\n\n"
    f"🌐 Main Website: <b>{SUNO_TARGET_DOMAIN}</b>"
)

settings_text = (
    "⚙️ <b>Your Bot Settings</b>\n\n"
    "Here you will soon be able to configure your download preferences, notification alerts, and audio quality formats! 🎛️\n\n"
    "<i>(Coming soon as we connect the web app database! Stay tuned 🚀)</i>"
)

token_text = (
    "🔑 <b>Account Token Management</b>\n\n"
    "To link your Telegram account with your profile on <b>sunoaisongdownload.online</b>, "
    "you will be able to generate and submit your access token here.\n\n"
    "<i>(This will soon let the bot sync downloads directly with your web account! 🌐)</i>"
)


def get_telegram_verification_success_message() -> str:
    return (
        "🎉 <b>Telegram Account Verified!</b>\n\n"
        "✅ Your Telegram account has been successfully linked "
        "to your web account.\n\n"
        "🔗 <b>Connection status:</b> Active\n"
        "👤 Your account is now connected and ready to use.\n\n"
        "🚀 You can now use this bot to interact with your "
        "Suno account directly from Telegram.\n\n"
        "✨ You're all set! Let's get started."
    )


def get_telegram_verification_failed_message() -> str:
    return (
        "⚠️ <b>Telegram Account Not Verified</b>\n\n"
        "❌ We couldn't verify this Telegram account with the "
        "account you used to generate this link.\n\n"
        "🔍 Please make sure you opened this bot using the "
        "Telegram connection link from your web account.\n\n"
        "💡 If you haven't linked your Telegram account yet, "
        "please go back to the website and generate a new "
        "connection link.\n\n"
        "🆘 If you believe this is a mistake, please contact support."
    )


def generate_successful_song_caption(
    song_info: SongInfo,
    star_cost: int | None = None,
) -> str:
    """
    The text to shows in caption when song data is fetched successfully
    Here this will generate and shows to the user
    """
    song_details_text = generate_song_details_only(
        song_data=song_info,
    )

    if star_cost:
        if settings.song.cost_applicable:
            cost_txt = (
                f"━━━━━━━━━━━━━━━━━━\n" f"💳 <b>Cost:</b> <b>{star_cost} Stars ⭐</b>"
            )

        else:
            cost_txt = (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"\n💳 <b>{star_cost} Stars ⭐</b>\n"
                f"(🎁 <b>Limited Offer: 🆓 FREE DOWNLOAD!</b>)"
            )

    else:
        cost_txt = ""

    caption = (
        "🎵 <b>Song Details 👇👇👇</b>\n\n" f"{song_details_text}" f"\n" f"{cost_txt}"
    )

    return caption


def generate_song_details_only(
    song_data: SongInfo,
):

    song_title = escape(song_data.title)
    # song_id = escape(song_data.id)
    artist_name = escape(song_data.artist) if song_data.artist else "Unknown Artist"

    # Build clickable profile URL if handle exists, otherwise just show the name
    if song_data.artist_username:
        profile_url = f"https://suno.com/@{song_data.artist_username}"
        artist_display = f"<a href='{profile_url}'><b>{artist_name}</b></a>"
    else:
        artist_display = f"<b>{artist_name}</b>"

    duration_text = escape(song_data.duration) if song_data.duration else "N/A"
    created_text = escape(song_data.created_date) if song_data.created_date else "N/A"
    plays_text = f"{song_data.plays:,}" if song_data.plays is not None else "N/A"
    likes_text = f"{song_data.likes:,}" if song_data.likes is not None else "N/A"

    song_details = (
        f"🎧 <b>Title:</b> <a href='{song_data.song_url_for_browser}'><b>{song_title}</b></a>\n"
        f"🎤 <b>Artist:</b> {artist_display}\n"
        f"⏱️ <b>Duration:</b> <code>{duration_text}</code>\n"
        f"📅 <b>Released:</b> <code>{created_text}</code>\n"
        f"👀 <b>Plays:</b> <code>{plays_text}</code>"
        f" | "
        f"❤️ <b>Likes:</b> <code>{likes_text}</code>"
    )

    return song_details


def generate_non_suno_link_received_text(
    wrong_url: str,
) -> str:
    random_songs = get_random_demo_songs_links(3)
    links_formatted = "\n".join([f"<code>{link}</code>" for link in random_songs])

    txt = (
        f"⚠️ <b>Invalid Link Detected!</b>\n\n"
        f"Your link (<code>{wrong_url}</code>) does not match our platform "
        f"(<code>{SUNO_TARGET_DOMAIN}</code>).\n\n"
        f"💡 <i>Please send a valid song link directly from our website.</i>\n\n"
        f"Send Me Back Any Link From the Given List."
        f"📋 <b>Try copying one of these working demo links to test:</b>\n"
        f"{links_formatted}"
    )
    return txt


def generate_wrong_suno_link_received_text() -> str:
    """
    Generates a helpful error message when a user sends
    an invalid or unsupported Suno link,
    complete with working demo links for them to test.
    """

    random_songs = get_random_demo_songs_links(3)
    links_formatted = "\n".join([f"<code>{link}</code>" for link in random_songs])

    text = (
        "❌ <b>Invalid Song Link</b>\n\n"
        f"The link you sent doesn't appear to be a valid Suno song URL.\n\n"
        "💡 <b>Tip:</b> Make sure you are sending a direct link to an individual Suno song or track, rather than a profile or generator page.\n\n"
        "📋 <b>Try copying and testing one of these working demo links instead:</b>\n\n"
        f"{links_formatted}\n\n"
        "✨ <i>Send a valid link whenever you're ready!</i>"
    )
    return text


def generate_suno_link_received_confirmation_message(
    url: str,
):
    """
    When user send a suno link the first message it will send sayin
    him to wait until server verifies the song later this text will remove
    """

    txt = (
        f"🎵 <b>Suno Link Received!</b> ✨\n\n"
        f"🔗 <b>Source URL</b>\n"
        f'🔗 <a href="{url}"><b>Open Song in Suno App</b></a>\n\n'
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🔍 <b>Fetching song details...</b>\n\n"
        f"⏳ Please wait while I:\n"
        f"• 🎧 Identify the song\n"
        f"• 🖼️ Fetch the cover artwork\n"
        f"• 🎵 Prepare the audio details\n"
        f"• 📥 Get everything ready for you\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🚀 <i>Almost there! Your song details will appear below shortly...</i> 🎶"
    )
    return txt


def generate_no_link_received_text() -> str:
    """
    Generates a helpful message when the user sends a message
    without any URL, including a few demo song links.
    """

    random_songs = get_random_demo_songs_links(3)
    links_formatted = "\n".join([f"🎵 <code>{link}</code>" for link in random_songs])

    return (
        "🔗 <b>No Song Link Found</b>\n\n"
        "I couldn't find a link in your message.\n\n"
        "📥 <b>How to use the bot:</b>\n"
        "Send me a direct link to a Suno song from our website, "
        "and I'll fetch the song details for you. 🎶\n\n"
        "💡 <b>Not sure what to send?</b>\n"
        "Try one of these working demo songs:\n\n"
        f"{links_formatted}\n\n"
        "✨ <i>Just copy and send one of the links above to try it!</i>"
    )


def generate_wrong_link_received_caption(
    wrong_url: str,
) -> str:
    caption = (
        "The link you sent isn't a valid <b>Suno song URL</b>.\n\n"
        "🔗 <b>Received:</b>\n"
        f"<code>{escape(wrong_url)}</code>\n\n"
        "👀 Here's a preview of the page that link opens.\n\n"
        "🎵 Please send a <b>Suno song link</b> if you'd like me to download the song."
    )
    return caption


def get_not_logged_in_message() -> str:
    return (
        "🔒 You are not logged in.\n\n"
        "Please log in to see your downloaded songs, "
        "or buy Premium to unlock your personal download history."
    )


def get_downloads_count_message(count: int) -> str:
    return f"🎵 You have {count} downloaded songs in your account."
