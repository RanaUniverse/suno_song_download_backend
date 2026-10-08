"""
app/bot_tg/utils.py

Here i will write some code which will help to
get the correct things for differne purpose
"""

from urllib.parse import urlparse


from telegram import MessageEntity


from app.config import settings

SUNO_TARGET_DOMAIN = settings.external.suno_target_domain


def extract_valid_song_link_from_message_entities(
    urls_dict: dict[MessageEntity, str],
    target_domain: str = SUNO_TARGET_DOMAIN,
) -> tuple[bool, str]:
    """
    This will try to match if the link pass here belongs
    to the song service i use ie suno.com

    If this got match then it will give me true and the link,
    if it not match it will give me false, last_link user send in the text
    """

    valid_url = None
    formatted_url = ""

    for _, url_text in urls_dict.items():
        if url_text.startswith(("http://", "https://")):
            formatted_url = url_text
        else:
            formatted_url = "https://" + url_text

        parsed_url = urlparse(formatted_url)
        domain = parsed_url.netloc.lower()

        if domain == SUNO_TARGET_DOMAIN or domain.endswith(f".{target_domain}"):
            valid_url = formatted_url
            break

    if valid_url:
        return True, valid_url
    else:
        return False, formatted_url
