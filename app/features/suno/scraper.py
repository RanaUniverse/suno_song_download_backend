"""
app/features/suno/scraper.py

"""

import re
import requests

from bs4 import BeautifulSoup
from app.features.suno.models import SongInfo


from .models import SongInfo
from app.config import settings
from .models_hook import HookResponse

from app.constants import UUID_REGEX

headers = settings.suno.share_api_headers


class AudioSongScraper:
    """Scrape metadata and audio URLs from a regular Suno song page."""

    def __init__(
        self,
        session: requests.Session | None = None,
    ):
        self.session = session or requests.Session()

    @staticmethod
    def extract_song_id(
        value: str,
    ) -> str | None:
        """
        It will specefically check if the song_id is correct
        and then return this or None
        """
        match = UUID_REGEX.search(value)
        return match.group(1) if match else None

    def scrape(
        self,
        song_html_text: str,
        audio_url: str,
        large_id: str | None = None,
    ) -> SongInfo:
        """
        Fetch hook metadata and its original clip's audio information.

        SongInfo.id is the original clip ID so an existing audio downloader
        can continue using it. SongInfo.hook_id identifies the hook itself.
        """

        html = song_html_text
        soup = BeautifulSoup(
            html,
            "html.parser",
        )
        if not large_id:
            large_id = ""

        info = SongInfo(
            id=large_id,
            audio_url=audio_url,
            base_audio_id=large_id or "",
        )

        # Extract Title first look at title property then twitter part
        og_title = soup.find("meta", property="og:title") or soup.find(
            "meta", {"name": "twitter:title"}
        )

        content = og_title.get("content") if og_title else None

        if isinstance(content, str):
            title_clean = content.replace(" | Suno", "").replace(" on Suno", "").strip()

            if title_clean:
                info.title = title_clean

        # Extract Cover Image
        og_image = soup.find("meta", property="og:image") or soup.find(
            "meta", {"name": "twitter:image"}
        )

        # This will give the correct image url i checked with song & hook
        image_content = og_image.get("content") if og_image else None
        if isinstance(image_content, str):
            info.image_url = image_content

        # Extract Description / Prompt
        og_desc = soup.find("meta", property="og:description") or soup.find(
            "meta", {"name": "description"}
        )
        description_content = og_desc.get("content") if og_desc else None
        if isinstance(description_content, str):
            info.prompt = description_content

        # Extract Style Tags
        tags_match = re.search(r"\"tags\"\s*:\s*\"([^\"]+)\"", html)
        if tags_match:
            info.tags = tags_match.group(1)

        # Search for CloudFront audio URL in the HTML
        cf_matches = re.findall(
            r'https?://[^\s"\'<>\\]+\.cloudfront\.net/[^\s"\'<>\\]+\.(?:m4a|mp3|wav)',
            html,
        )
        if cf_matches:
            info.audio_url = cf_matches[0]

        elif info.id:
            info.audio_url = (
                f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{info.id}.m4a"
            )
            # TODO i will later thinks to change this audio_url if suno change this

        if not info.image_url and info.id:
            info.image_url = f"https://cdn2.suno.ai/image_large_{info.id}.jpeg"

        return info


# The below part i done already

# # Accept a UUID or a direct song URL.
# if not url_or_id.startswith(("http://", "https://")):
#     song_id = self.extract_song_id(url_or_id)

#     if not song_id:
#         raise ValueError(f"Invalid Suno song URL or ID: {url_or_id}")

#     url = f"https://suno.com/song/{song_id}"

# else:
#     url = url_or_id

# response = self.session.get(
#     url,
#     timeout=15,
#     allow_redirects=True,
# )
# response.raise_for_status()
# final_url = response.url.rstrip("/")


class HookSongScraper:
    """
    Fetch hook metadata from Suno's video-hook API.
    """

    API_URL = "https://studio-api-prod.suno.com/api/video/hooks/{}"

    def __init__(
        self,
        session: requests.Session | None = None,
    ):
        self.session = session or requests.Session()

    def scrape(
        self,
        hook_id: str,
    ) -> SongInfo:
        """
        Fetch hook metadata and its original clip's audio information.

        SongInfo.id is the original clip ID so an existing audio downloader
        can continue using it. SongInfo.hook_id identifies the hook itself.
        """
        hook_id = hook_id.strip()

        if not hook_id:
            raise ValueError("A hook ID is required")

        # this will call a new get to new api json
        response = self.session.get(
            self.API_URL.format(hook_id),
            headers=settings.suno.share_api_headers,
            timeout=15,
        )
        response.raise_for_status()

        # data = response.json()
        # clip = data.get("clip", {})
        # metadata = clip.get("metadata", {})
        # print("Clippppppppp", clip)

        # Now i have convertd this to pydantic's basemodle instance for
        # easy access beloe

        data = HookResponse.model_validate(response.json())

        # This will return the main song info's data hwer

        info = SongInfo(
            id=data.id or "",
            type="hook",
            title=data.clip.title,
            base_audio_id=data.base_audio_id or "",
            audio_url=data.base_audio_url,
            video_url=data.video_url,
            image_url=data.thumbnail_image_url,
            # tags=data.clip.metadata.tags,
            # prompt=data.clip.metadata.prompt,
        )

        return info
