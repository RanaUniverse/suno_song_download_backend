"""
app/features/suno/scraper.py

"""

import json
import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Tag
from app.features.suno.models import SongInfo


from .models import SongInfo
from app.config import settings
from .models_hook import HookResponse

from app.constants import UUID_REGEX
from .models import ArtistInfo

#


headers = settings.suno.share_api_headers


def extract_artist_info(
    # description: str,
    description_tag: Tag | None = None,
) -> ArtistInfo | None:
    """
    This will extract the information from the description like this,

    This content part is coming here as description
    <meta
    name="description"
    content="दिल मेरा नाचे by Rana Universe (@ranauniverse). Listen and make your own on Suno."
    />
    """
    if description_tag is None:
        return None

    description = description_tag.get("content", "")

    if isinstance(description, str):
        match = re.search(
            r"\bby\s+(.+?)\s+\(@([^)]+)\)",
            description,
            re.IGNORECASE,
        )

        if not match:
            return None

        return ArtistInfo(
            name=match.group(1).strip(),
            username=match.group(2).strip(),
        )


def collect_payload(html: str):
    """
    Replicates the JavaScript collectPayload function to grab Next.js flight chunks.
    """
    pattern = r'self\.__next_f\.push\(\[\s*1\s*,\s*"((?:\\.|[^"\\])*)"\s*\]\)'
    matches = re.findall(pattern, html)
    out = ""
    for m in matches:
        try:
            # Safely unescape the string literal
            decoded = json.loads(f'"{m}"')
            out += decoded
        except Exception:
            out += m.replace(r"\"", '"').replace(r"\\", "\\").replace(r"\n", "\n")
    return out


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
        print(og_title)

        content = og_title.get("content") if og_title else None

        if isinstance(content, str):
            title_clean = content

            if title_clean:
                info.title = title_clean

        # Extract Cover Image
        og_image = soup.find("meta", property="og:image") or soup.find(
            "meta", {"name": "twitter:image"}
        )

        image_content = og_image.get("content") if og_image else None
        if isinstance(image_content, str):
            info.image_url = image_content

        # TODO i will add prompt later
        # Extract Description / Prompt
        # og_desc = soup.find("meta", property="og:description") or soup.find(
        #     "meta", {"name": "description"}
        # )
        # description_content = og_desc.get("content") if og_desc else None
        # if isinstance(description_content, str):
        #     info.prompt = description_content

        # Extract Style Tags
        tags_match = re.search(r'\\"tags\\":\\"(.*?)\\"', html)

        if tags_match:
            info.tags = tags_match.group(1).replace('\\"', '"').replace("\\\\", "\\")

        # Search for CloudFront audio URL in the HTML source url to download
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

        description_tag = soup.find("meta", attrs={"name": "description"})
        artist_info = extract_artist_info(description_tag)

        if artist_info:
            info.artist = artist_info.name
            info.artist_username = artist_info.username

        payload = collect_payload(html)

        # now i will get the artist name here
        # Extract artist name and username from page description

        # 4. Extract Duration (Seconds and formatted MM:SS)
        dur_match = re.search(r'"duration"\s*:\s*([0-9.]+)', payload)
        if dur_match:
            secs = float(dur_match.group(1))
            duration_secs = round(secs)
            mins = int(duration_secs // 60)
            rem = int(duration_secs % 60)
            duration_str = f"{mins}:{rem:02d}"
            info.duration_in_seconds = duration_secs
            info.duration = duration_str

        # 5. Extract Created Date (YYYY-MM-DD)
        date_match = re.search(r'"created_at"\s*:\s*"([^"]+)"', payload)
        if date_match:
            created_date = date_match.group(1)[:10]
            info.created_date = created_date

        # 6. Extract Plays & Likes
        plays_match = re.search(r'"play_count"\s*:\s*(\d+)', payload)
        if plays_match:
            plays_count = int(plays_match.group(1))
            info.plays = plays_count

        likes_match = re.search(r'"upvote_count"\s*:\s*(\d+)', payload)
        if likes_match:
            likes_count = int(likes_match.group(1))
            info.likes = likes_count

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
