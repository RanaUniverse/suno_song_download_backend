"""
app/features/suno/scraper.py

"""

# import re
# from typing import Literal
# from urllib.parse import urlparse
import requests

# from bs4 import BeautifulSoup
# from pydantic import BaseModel
from app.features.suno.models import SongInfo


from .models import SongInfo
from app.config import settings
from .models_hook import HookResponse

headers = settings.suno.share_api_headers


class AudioSongScraper:
    pass


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

        info = SongInfo(
            id=data.id,
            type="hook",
            title=data.clip.title,
            audio_url=data.base_audio_url,
            video_url=data.video_url,
            image_url=data.thumbnail_image_url,
            tags=data.clip.metadata.tags,
            prompt=data.clip.metadata.prompt,
            source_url=f"https://suno.com/hook/{hook_id}",
        )
        print(info)

        return info
