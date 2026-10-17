"""
suno_downloader.py

# Suno AI Music Downloader & Decryptor
# Download and decrypt Suno AI songs (Mango DRM / AES-128-CTR system)
# Generating standard high-fidelity 320 kbps MP3 files with cover art and lyrics.

"""

import os
from pathlib import Path
import re
import sys

# import json
import base64
import hashlib
import subprocess

# import urllib.parse
from typing import (
    Optional,
    # Dict,
    Any,
    Callable,
    TextIO,
)
import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


import imageio_ffmpeg  # type: ignore This was pystub issu


from app.config import settings

from app.constants import UUID_REGEX
from app.features.suno.models import (
    AudioSampleResult,
    DownloadResult,
    SampleDownloadResult,
    SongInfo,
    SeparationResult,
)
from app.shared.logger_related import RanaLogger
from .suno.models import ResolvedSunoLink

from .suno.scraper import HookSongScraper, AudioSongScraper
from .suno.storage import get_base_name, download_cover_image
from app.config import AudioFormat, SUPPORTED_AUDIO_FORMAT

DEFAULT_HEADERS = settings.suno.default_headers

# This below part is for handle different type of text output
# to the terminal or whatsoever


def configure_output(stream: TextIO) -> None:
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(  # type: ignore ; attr-defined
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            pass


configure_output(sys.stdout)
configure_output(sys.stderr)


class SunoScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def resolve_share_code_new(
        self,
        share_code: str,
    ) -> ResolvedSunoLink | None:
        """
        Attempts to resolve a short Suno shared link (/s/CODE) to the actual song ID.
        Here i will pass the short id to get the song info

        It returns the large Content ID and type of this if any
        """

        endpoints = [
            f"https://studio-api.prod.suno.com/api/share/code/{share_code}",
            f"https://studio-api-prod.suno.com/api/share/code/{share_code}",
        ]

        headers = settings.suno.share_api_headers

        for ep in endpoints:
            try:
                res = self.session.get(ep, headers=headers, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    content_type = data.get("content_type")
                    content_id = data.get("content_id")

                    if not isinstance(content_type, str):
                        raise ValueError("Missing or invalid content_type")

                    if not isinstance(content_id, str):
                        raise ValueError("Missing or invalid content_id")

                    if content_type not in ("song", "hook"):
                        raise ValueError(
                            f"Unsupported Suno content type: {content_type}"
                        )

                    # after i get the content_id i will try to check if this looks
                    # like the uuid of suno if yes then say this is id
                    if content_type == "hook":
                        song_info = HookSongScraper().scrape(content_id)
                        return ResolvedSunoLink(
                            type=song_info.type,
                            content_id=song_info.id,
                        )

                    # TODO now later i will use the logic of seaprate the beautifulsoup

                    elif (
                        content_type == "song"
                        and content_id
                        and UUID_REGEX.search(str(content_id))
                    ):
                        return ResolvedSunoLink(
                            content_id=content_id,
                            type=content_type,
                        )

                    else:
                        RanaLogger.warning(f"Here is somethings wrong no song no hook")
                        return

            except Exception as e:
                RanaLogger.warning(f"{e}")
                pass

        return None

    def extract_song_id(
        self,
        url_or_id: str,
    ) -> str | None:
        """
        Extracts the Suno song Large UUID.
        """
        match = UUID_REGEX.search(url_or_id)
        if match:
            return match.group(1)
        return None

    def scrape_song_info(
        self,
        url: str,
    ) -> SongInfo:
        """
        This wants the large song uuid

        Supports:
        - https://suno.com/song/<UUID>
        - https://suno.com/hook/<UUID>
        - https://suno.com/s/<SHARE_CODE>
        Extracts metadata, image, and URLs from the Suno page.
        This Function will return the updated SongInfo BaseModel class
        """

        url = url.strip()

        # so this first check if the large_id is working here not url
        if not url.startswith("http"):
            raise ValueError(f"Link Must Start with HTTP Protocol")
            # later i will want to have the allow by large_id

            # song_id = self.extract_song_id(url)
            # if song_id:
            #     url = f"https://suno.com/song/{song_id}"
            # else:
            #     raise ValueError(f"Invalid URL or ID: {url}")

        # Now i will check if there is /hook/ in the url then i will just
        # directly use teh hook logic

        response = self.session.get(
            url,
            timeout=15,
            allow_redirects=True,
        )

        final_url = (response.url).rstrip("/")

        # If it is a short link /s/CODE, try to resolve it using the official Suno API
        share_match = re.search(r"/s/([a-zA-Z0-9_\-]+)", url)
        if share_match:
            share_code = share_match.group(1)
            resolved = self.resolve_share_code_new(
                share_code,
            )

            if resolved and resolved.type == "hook":
                scrap_data = HookSongScraper().scrape(
                    resolved.content_id,
                )
                url = scrap_data.song_url_for_browser

            elif resolved and resolved.type == "song":
                url = resolved.full_url

        # 1. Direct hook URL: scrape immediately.
        hook_match = re.search(
            r"/hook/([a-fA-F0-9-]+)(?:[/?#]|$)",
            final_url,
        )

        if hook_match:
            hook_id = hook_match.group(1)

            if not UUID_REGEX.fullmatch(hook_id):
                raise ValueError(f"Invalid Suno hook ID: {hook_id}")

            scrap_info = HookSongScraper().scrape(hook_id)
            url = scrap_info.song_url_for_browser
            print("Hook song get transfering this to normal /song")

        # Make an HTTP request following redirects
        # after i will get the proper url i will say my
        # hoook or song to make another get request

        song_id = self.extract_song_id(url)

        # Check if it redirected to the Suno homepage (broken, private, or expired link)
        is_home_redirect = final_url in settings.suno.home_urls

        if is_home_redirect and not song_id:
            if share_match or "/s/" in url:
                raise ValueError(
                    f"Could not find the song from the short link:\n'{url}'\n\n"
                    "The link does not exist, is private, or has expired on Suno "
                    "(Suno's servers redirect it to the home page).\n\n"
                    "👉 Solution: Open the song in your browser (or in the Suno app), "
                    "click on the title, and copy the direct link containing the song ID:\n"
                    "https://suno.com/song/12345678-abcd-4ef0-9012-123456789abc"
                )
            else:
                raise ValueError(
                    f"The link redirects to Suno's home page without finding "
                    f"the song:\n'{url}'\n\n"
                    "Please use the full song link:\n"
                    "https://suno.com/song/12345678-abcd-4ef0-9012-123456789abc"
                )

        # This will ensure if user first enter large url it will done before
        # else it will use redicrtt and then use this to get the song id
        if not song_id:
            song_id = self.extract_song_id(final_url)

        # If the UUID has not been found yet and it is not
        # the home page, search in the HTML meta tags
        if not song_id and not is_home_redirect:
            soup_pre = BeautifulSoup(response.text, "html.parser")
            og_url = soup_pre.find("meta", property="og:url")

            if og_url:
                content = og_url.get("content")
                if isinstance(content, str) and content:
                    song_id = self.extract_song_id(content)

        if not song_id:
            raise ValueError(
                f"Could not detect the song ID in '{url}'.\n\n"
                "Make sure to paste a direct link to a Suno song:\n"
                "Example: https://suno.com/song/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        # Now below runs means this chekcing of the link is good with suno song
        scrap_data = AudioSongScraper().scrape(
            song_html_text=response.text,
            audio_url=final_url,
            large_id=song_id,
        )
        return scrap_data

    def decrypt_and_download(
        self,
        song_id: str,
        stream_url: str,
        output_audio_path: Path,
        audio_format: AudioFormat = "m4a",
        keep_m4a: bool = False,
        progress_callback: Optional[Callable[[str, int, int, float], None]] = None,
    ) -> Path | None:
        """
        output_audio_path -> i need to make sure this exists with its parents dir

        The caller is responsible for creating the output directory.

        Decrypts Suno audio using the Mango system
        (AES-GCM unwrapping + AES-128-CTR stream decryption)
        and converts it to the desired format
        (M4A, MP3 320 kbps or uncompressed WAV).
        """

        fmt = audio_format.lower().strip()
        if fmt not in SUPPORTED_AUDIO_FORMAT:
            RanaLogger.warning(f"Unsupported audio format: {audio_format}")
            return None

        if progress_callback:
            progress_callback("License", 0, 0, 10.0)

        # temp_decrypted: Path | None = None

        # 1. Get Mango license keys
        rights_url = "https://studio-api.prod.suno.com/api/mango/rights"
        payload = {
            "content_params": {
                "content_id": song_id,
                "content_type": "clip",
            }
        }
        rights_res = self.session.post(
            rights_url,
            json=payload,
            timeout=15,
        )
        if rights_res.status_code != 200:
            raise Exception(
                f"Failed to obtain Suno audio license (HTTP {rights_res.status_code})"
            )

        rights_data = rights_res.json()
        glt = rights_data["glt"]
        wrapped_key_b64 = rights_data["key"]
        wrapped_iv_b64 = rights_data["iv"]

        # 2. Unpack key and initialization vector (AES-GCM with GLT SHA256)
        user_key = hashlib.sha256(glt.encode("utf-8")).digest()
        aes_gcm = AESGCM(user_key)
        aad = song_id.encode("utf-8")

        wrapped_key = base64.b64decode(wrapped_key_b64)
        content_key = aes_gcm.decrypt(wrapped_key[:12], wrapped_key[12:], aad)

        wrapped_iv = base64.b64decode(wrapped_iv_b64)
        content_iv = aes_gcm.decrypt(wrapped_iv[:12], wrapped_iv[12:], aad)

        # 3. Download the encrypted stream with progress
        if progress_callback:
            progress_callback("Downloading", 0, 0, 25.0)

        res = self.session.get(
            stream_url,
            stream=True,
            timeout=30,
        )
        if res.status_code != 200:
            RanaLogger.error(
                f"Error downloading audio stream (HTTP {res.status_code})",
            )
            return None

        total_size = int(res.headers.get("content-length", 0))
        encrypted_chunks: list[bytes] = []
        downloaded = 0

        for chunk in res.iter_content(chunk_size=64 * 1024):
            if chunk:
                encrypted_chunks.append(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    pct = 25.0 + ((downloaded / total_size) * 50.0)
                    progress_callback("Downloading", downloaded, total_size, pct)

        encrypted_data = b"".join(encrypted_chunks)
        if len(encrypted_data) < 50000:
            raise Exception("The downloaded file is incomplete or empty.")

        # 4. Decrypt with AES-128-CTR
        if progress_callback:
            progress_callback("Decrypting", downloaded, total_size, 80.0)

        cipher = Cipher(
            algorithms.AES(content_key),
            modes.CTR(content_iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_audio = decryptor.update(encrypted_data) + decryptor.finalize()

        # M4A is already the decrypted source stream. Write it directly to its
        # final .m4a filename; do not invoke FFmpeg or perform a re-encode.
        if fmt == "m4a":
            output_audio_path.write_bytes(decrypted_audio)
            # output_path.write_bytes(decrypted_audio)
            if progress_callback:
                progress_callback("Completed", downloaded, total_size, 100.0)
            return output_audio_path

        # MP3/WAV need FFmpeg, so keep a short-lived M4A input only for those
        # conversion requests. --keep-m4a preserves the same source beside it.

        # m4a_path = output_audio_path.rsplit(".", 1)[0] + ".m4a"
        m4a_path = output_audio_path.with_suffix(".m4a")
        if keep_m4a:
            m4a_path.write_bytes(decrypted_audio)
            # with open(m4a_path, "wb") as f:
            #     f.write(decrypted_audio)

        # temp_decrypted = output_audio_path + ".part.m4a"
        # with open(temp_decrypted, "wb") as f:
        #     f.write(decrypted_audio)

        temp_decrypted = output_audio_path.with_name(
            f"{output_audio_path.stem}.part.m4a"
        )
        temp_decrypted.write_bytes(decrypted_audio)

        # 5. Convert to standard MP3 or Lossless WAV with FFmpeg
        if progress_callback:
            progress_callback("Converting", downloaded, total_size, 90.0)

        if fmt == "wav":
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i",
                str(temp_decrypted),
                "-vn",
                "-c:a",
                "pcm_s16le",
                str(output_audio_path),
            ]
        else:
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i",
                str(temp_decrypted),
                "-vn",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "320k",
                str(output_audio_path),
            ]

        conv_res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Clean up temporary file
        # if os.path.exists(temp_decrypted):
        #     try:
        #         os.remove(temp_decrypted)
        #     except Exception:
        #         pass

        # Clean up the temporary input.
        try:
            temp_decrypted.unlink(missing_ok=True)
        except OSError as exc:
            RanaLogger.warning(f"Could not remove temporary file: {exc}")

        if conv_res.returncode != 0:
            RanaLogger.error(f"FFmpeg conversion failed: {conv_res.stderr}")
            return None
            # Fallback: rename the decrypted m4a if ffmpeg fails
            # fallback_m4a = output_audio_path.rsplit(".", 1)[0] + ".m4a"
            # with open(fallback_m4a, "wb") as f:
            #     f.write(decrypted_audio)
            # return fallback_m4a

        if progress_callback:
            progress_callback("Completed", downloaded, total_size, 100.0)

        return output_audio_path

    def get_audio_duration_from_ffmpeg(
        self,
        file_path_path: Path | None = None,
        file_path: str = "",
    ) -> float:
        """
        Gets the duration of the audio file in seconds using FFmpeg.
        """
        if not file_path_path:
            return 0.0

        try:
            cmd = [self.ffmpeg_exe, "-i", str(file_path_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        # TODO later i will remove all the below thigns
        if not os.path.exists(file_path):
            return 0.0
        try:
            cmd = [self.ffmpeg_exe, "-i", file_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0

    def create_audio_sample(
        self,
        input_mp3: str,
        output_sample_mp3: Optional[str] = None,
        start_sec: float = 0.0,
        duration_sec: Optional[float] = None,
        apply_fade: bool = True,
    ) -> AudioSampleResult:
        """
        Generates an MP3/WAV sample/preview of a portion of the song.
        If duration_sec is not specified, it is automatically calculated based on the total duration:
          - If duration is <= 60s: 30s sample.
          - If duration is <= 180s (3m): 60s (1m) sample.
          - If duration is > 180s (e.g., 4-5m): 120s (2m) sample or 45% of the total.
        """
        if not os.path.exists(input_mp3):
            raise FileNotFoundError(
                f"Audio file does not exist: {input_mp3}",
            )

        total_duration = self.get_audio_duration_from_ffmpeg(input_mp3)

        # Intelligent sample duration calculation
        if duration_sec is None or duration_sec <= 0:
            if total_duration <= 0:
                duration_sec = 60.0
            elif total_duration <= 60:
                duration_sec = min(30.0, total_duration)
            elif total_duration <= 180:
                duration_sec = 60.0
            else:
                # Example: 4-5 minute songs -> 2-minute sample (120s)
                duration_sec = min(120.0, total_duration * 0.45)

        # Ensure valid limits
        if total_duration > 0:
            start_sec = max(0.0, min(start_sec, max(0.0, total_duration - 5.0)))
            duration_sec = min(duration_sec, total_duration - start_sec)
        else:
            start_sec = max(0.0, start_sec)
            duration_sec = max(5.0, duration_sec)

        input_ext = os.path.splitext(input_mp3)[1].lower()
        if not output_sample_mp3:
            base, ext = os.path.splitext(input_mp3)
            dur_label = (
                f"{int(duration_sec)}s"
                if duration_sec < 60
                else (
                    f"{int(duration_sec // 60)}m{int(duration_sec % 60):02d}s"
                    if duration_sec % 60
                    else f"{int(duration_sec // 60)}m"
                )
            )
            output_sample_mp3 = f"{base}_muestra_{dur_label}{ext}"

        # Apply smoothing (fade-in and fade-out)
        filters = []
        if apply_fade and duration_sec >= 4.0:
            fade_in_len = min(1.5, duration_sec * 0.08)
            fade_out_len = min(2.5, duration_sec * 0.12)
            fade_out_start = max(0.1, duration_sec - fade_out_len)
            filters.append(f"afade=t=in:ss=0:d={fade_in_len:.2f}")
            filters.append(f"afade=t=out:st={fade_out_start:.2f}:d={fade_out_len:.2f}")

        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-ss",
            str(round(start_sec, 2)),
            "-t",
            str(round(duration_sec, 2)),
            "-i",
            input_mp3,
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        if input_ext == ".wav":
            cmd.extend(["-c:a", "pcm_s16le", output_sample_mp3])
        elif input_ext == ".m4a":
            cmd.extend(["-c:a", "aac", "-b:a", "192k", output_sample_mp3])
        else:
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", output_sample_mp3])

        conv_res = subprocess.run(cmd, capture_output=True, text=True)
        if conv_res.returncode != 0:
            raise Exception(f"Error generating sample with FFmpeg: {conv_res.stderr}")

        sample_duration = self.get_audio_duration_from_ffmpeg(output_sample_mp3)

        return AudioSampleResult(
            sample_path=output_sample_mp3,
            filename=os.path.basename(output_sample_mp3),
            total_duration=total_duration,
            start_sec=start_sec,
            duration_sec=duration_sec,
            actual_sample_duration=sample_duration,
        )

    def download_sample_direct(
        self,
        url: str,
        duration_sec: Optional[Any] = None,
        start_sec: float = 0.0,
        output_dir: str = "downloads",
        audio_format: str = "mp3",
        apply_fade: bool = True,
        save_cover: bool = True,
        progress_callback: Optional[Callable[[str, int, int, float], None]] = None,
    ) -> SampleDownloadResult:
        """
        Directly downloads and generates an audio sample (preview) from a Suno URL,
        without needing to save the full song to disk beforehand.
        """
        info = self.scrape_song_info(url)
        os.makedirs(output_dir, exist_ok=True)

        base_name = get_base_name(info)

        fmt = audio_format.lower().strip()
        if fmt not in {"m4a", "mp3", "wav"}:
            raise ValueError(f"Unsupported audio format: {audio_format}")
        ext = fmt

        # 1. Check if the full song was already downloaded previously in the folder
        candidate_audio = os.path.join(output_dir, f"{base_name}.{ext}")
        if not os.path.exists(candidate_audio):
            for alt_ext in ("m4a", "mp3", "wav"):
                if alt_ext == ext:
                    continue
                alt_path = os.path.join(output_dir, f"{base_name}.{alt_ext}")
                if os.path.exists(alt_path):
                    candidate_audio = alt_path
                    break

        if os.path.exists(candidate_audio) and os.path.getsize(candidate_audio) > 50000:
            tot = self.get_audio_duration_from_ffmpeg(candidate_audio)
            dur_calc = None
            if duration_sec == "half":
                dur_calc = max(15.0, tot * 0.5) if tot > 0 else 60.0
            elif isinstance(duration_sec, (int, float)):
                dur_calc = float(duration_sec)

            sample = self.create_audio_sample(
                candidate_audio,
                start_sec=start_sec,
                duration_sec=dur_calc,
                apply_fade=apply_fade,
            )

            cover_path = None
            if save_cover:
                im_path = download_cover_image(
                    info=info,
                    destination_folder=output_dir,
                )
                if im_path:
                    print(f"Image has saved into for Sample direct the {im_path}")
                    cover_path = im_path

            return SampleDownloadResult(
                info=info,
                sample_path=sample.sample_path,
                filename=sample.filename,
                total_duration=sample.total_duration,
                start_sec=sample.start_sec,
                duration_sec=sample.duration_sec,
                actual_sample_duration=sample.actual_sample_duration,
                cover_path=cover_path,
                format=ext,
            )

        # 2. If the complete one does not exist, download and decrypt
        # the stream to a temporary file that will be deleted upon completion
        stream_url = (
            info.base_audio_id
            or f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{song_id}.m4a"
        )
        temp_decrypted = os.path.join(
            output_dir, f".tmp_sample_{song_id[:8]}_{os.getpid()}.m4a"
        )

        try:
            if progress_callback:
                progress_callback("Connecting", 0, 0, 10.0)

            rights_url = "https://audiopipe.suno.ai/rights"
            payload = {
                "license_type": "user",
                "content": {
                    "content_id": song_id,
                    "content_type": "clip",
                },
            }
            rights_res = self.session.post(
                rights_url,
                json=payload,
                timeout=15,
            )

            if rights_res.status_code != 200:
                raise Exception(
                    f"Failed to obtain Suno audio license (HTTP {rights_res.status_code})"
                )

            rights_data = rights_res.json()
            glt = rights_data["glt"]
            wrapped_key_b64 = rights_data["key"]
            wrapped_iv_b64 = rights_data["iv"]

            user_key = hashlib.sha256(glt.encode("utf-8")).digest()
            aes_gcm = AESGCM(user_key)
            aad = song_id.encode("utf-8")

            wrapped_key = base64.b64decode(wrapped_key_b64)
            content_key = aes_gcm.decrypt(wrapped_key[:12], wrapped_key[12:], aad)

            wrapped_iv = base64.b64decode(wrapped_iv_b64)
            content_iv = aes_gcm.decrypt(wrapped_iv[:12], wrapped_iv[12:], aad)

            if progress_callback:
                progress_callback("Downloading Stream", 0, 0, 25.0)

            res = self.session.get(stream_url, stream=True, timeout=30)
            if res.status_code != 200:
                raise Exception(
                    f"Error downloading audio stream (HTTP {res.status_code})"
                )

            total_size = int(res.headers.get("content-length", 0))
            encrypted_chunks = []
            downloaded = 0
            for chunk in res.iter_content(chunk_size=64 * 1024):
                if chunk:
                    encrypted_chunks.append(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        pct = 25.0 + ((downloaded / total_size) * 45.0)
                        progress_callback(
                            "Downloading Stream", downloaded, total_size, pct
                        )

            encrypted_data = b"".join(encrypted_chunks)
            if len(encrypted_data) < 50000:
                raise Exception("The downloaded audio stream is incomplete or empty.")

            if progress_callback:
                progress_callback("Decrypting", downloaded, total_size, 75.0)

            cipher = Cipher(
                algorithms.AES(content_key),
                modes.CTR(content_iv),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            decrypted_audio = decryptor.update(encrypted_data) + decryptor.finalize()

            with open(temp_decrypted, "wb") as f:
                f.write(decrypted_audio)

            total_duration = self.get_audio_duration_from_ffmpeg(temp_decrypted)

            if duration_sec == "half":
                calc_dur = (
                    max(15.0, total_duration * 0.5) if total_duration > 0 else 60.0
                )
            elif isinstance(duration_sec, (int, float)) and duration_sec > 0:
                calc_dur = float(duration_sec)
            else:
                if total_duration <= 0:
                    calc_dur = 60.0
                elif total_duration <= 60:
                    calc_dur = min(30.0, total_duration)
                elif total_duration <= 180:
                    calc_dur = 60.0
                else:
                    calc_dur = min(120.0, total_duration * 0.45)

            if total_duration > 0:
                start_sec = max(0.0, min(start_sec, max(0.0, total_duration - 5.0)))
                calc_dur = min(calc_dur, total_duration - start_sec)
            else:
                start_sec = max(0.0, start_sec)
                calc_dur = max(5.0, calc_dur)

            dur_label = (
                f"{int(calc_dur)}s"
                if calc_dur < 60
                else (
                    f"{int(calc_dur // 60)}m{int(calc_dur % 60):02d}s"
                    if calc_dur % 60
                    else f"{int(calc_dur // 60)}m"
                )
            )
            output_sample_file = os.path.join(
                output_dir, f"{base_name}_sample_{dur_label}.{ext}"
            )

            if progress_callback:
                progress_callback("Creating Sample", downloaded, total_size, 85.0)

            filters = []
            if apply_fade and calc_dur >= 4.0:
                fade_in_len = min(1.5, calc_dur * 0.08)
                fade_out_len = min(2.5, calc_dur * 0.12)
                fade_out_start = max(0.1, calc_dur - fade_out_len)
                filters.append(f"afade=t=in:ss=0:d={fade_in_len:.2f}")
                filters.append(
                    f"afade=t=out:st={fade_out_start:.2f}:d={fade_out_len:.2f}"
                )

            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-ss",
                str(round(start_sec, 2)),
                "-t",
                str(round(calc_dur, 2)),
                "-i",
                temp_decrypted,
            ]
            if filters:
                cmd.extend(["-af", ",".join(filters)])

            if ext == "wav":
                cmd.extend(["-vn", "-c:a", "pcm_s16le", output_sample_file])
            elif ext == "m4a":
                cmd.extend(["-vn", "-c:a", "aac", "-b:a", "192k", output_sample_file])
            else:
                cmd.extend(
                    ["-vn", "-c:a", "libmp3lame", "-b:a", "320k", output_sample_file]
                )

            conv_res = subprocess.run(cmd, capture_output=True, text=True)
            if conv_res.returncode != 0:
                raise Exception(
                    f"Error generating sample with FFmpeg: {conv_res.stderr}"
                )

            sample_actual_duration = self.get_audio_duration_from_ffmpeg(
                output_sample_file
            )

            cover_path = None
            if save_cover:
                im_path = download_cover_image(
                    info=info,
                    destination_folder=output_dir,
                )
                if im_path:
                    print(
                        f"Image has saved into for download Sample direct the {im_path}"
                    )
                    cover_path = im_path

            if progress_callback:
                progress_callback("Completed", downloaded, total_size, 100.0)

            return SampleDownloadResult(
                info=info,
                sample_path=output_sample_file,
                filename=os.path.basename(output_sample_file),
                total_duration=total_duration,
                start_sec=start_sec,
                duration_sec=calc_dur,
                actual_sample_duration=sample_actual_duration,
                cover_path=cover_path,
                format=ext,
            )

        finally:
            if os.path.exists(temp_decrypted):
                try:
                    os.remove(temp_decrypted)
                except Exception:
                    pass

    def separate_vocals_and_instrumental(
        self,
        input_audio: str,
        output_dir: Optional[str] = None,
        output_format: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int, float], None]] = None,
    ) -> SeparationResult:
        """
        Separates a song into two independent tracks:
          1. Instrumental Track (Music without vocals with bass and rhythms preserved)
          2. Vocals Only (Acapella / Isolated vocals)
        Uses M/S phase stereo processing and high-precision DSP crossover filters.
        """
        if not os.path.exists(input_audio):
            raise FileNotFoundError(f"Audio file does not exist: {input_audio}")

        out_dir = output_dir or os.path.dirname(input_audio) or "downloads"
        os.makedirs(out_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_audio))[0]
        # Clean up previous suffixes if any
        for suffix in ["_instrumental_track", "_vocals_only", "_sample"]:
            if suffix in base_name:
                base_name = base_name.split(suffix)[0]

        fmt = (
            (
                output_format
                or ("wav" if input_audio.lower().endswith(".wav") else "mp3")
            )
            .lower()
            .strip()
        )
        if fmt not in {"m4a", "mp3", "wav"}:
            raise ValueError(f"Unsupported audio format: {output_format}")
        codec_args = (
            ["-c:a", "pcm_s16le"]
            if fmt == "wav"
            else (
                ["-c:a", "aac", "-b:a", "192k"]
                if fmt == "m4a"
                else ["-c:a", "libmp3lame", "-b:a", "320k"]
            )
        )

        instrumental_path = os.path.join(
            out_dir, f"{base_name}_instrumental_track.{fmt}"
        )
        vocals_path = os.path.join(out_dir, f"{base_name}_vocals_only.{fmt}")

        if (
            os.path.exists(instrumental_path)
            and os.path.exists(vocals_path)
            and os.path.getsize(instrumental_path) > 50000
            and os.path.getsize(vocals_path) > 50000
        ):
            dur = self.get_audio_duration_from_ffmpeg(instrumental_path)
            return SeparationResult(
                instrumental_path=instrumental_path,
                vocals_path=vocals_path,
                instrumental_filename=os.path.basename(instrumental_path),
                vocals_filename=os.path.basename(vocals_path),
                duration=dur,
                format=fmt,
            )

        if progress_callback:
            progress_callback("Separating Instrumental", 0, 0, 20.0)

        # Filter 1: Instrumental Track (Cancels center and preserves bass < 160Hz)
        inst_filter = (
            "[0:a]asplit=2[orig][orig_bass];"
            "[orig]pan=stereo|c0=c0-c1|c1=c1-c0,volume=1.5[sides];"
            "[orig_bass]lowpass=f=160[bass];"
            "[sides][bass]amix=inputs=2:weights=1 1[outa]"
        )
        cmd_inst = (
            [
                self.ffmpeg_exe,
                "-y",
                "-i",
                input_audio,
                "-filter_complex",
                inst_filter,
                "-map",
                "[outa]",
            ]
            + codec_args
            + [instrumental_path]
        )

        res_inst = subprocess.run(cmd_inst, capture_output=True, text=True)
        if res_inst.returncode != 0:
            raise Exception(f"Error generating instrumental track: {res_inst.stderr}")

        if progress_callback:
            progress_callback("separating vocals", 0, 0, 60.0)

        # Filter 2: Vocals Only (Isolation of vocal formants and central frequencies)
        vocal_filter = (
            "[0:a]asplit=2[full][highs];"
            "[full]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,highpass=f=180,lowpass=f=7500[vocal_mid];"
            "[highs]highpass=f=7500,volume=0.25[vocal_air];"
            "[vocal_mid][vocal_air]amix=inputs=2:weights=1.2 0.8[outa]"
        )
        cmd_vocal = (
            [
                self.ffmpeg_exe,
                "-y",
                "-i",
                input_audio,
                "-filter_complex",
                vocal_filter,
                "-map",
                "[outa]",
            ]
            + codec_args
            + [vocals_path]
        )

        res_vocal = subprocess.run(cmd_vocal, capture_output=True, text=True)
        if res_vocal.returncode != 0:
            raise Exception(f"Error isolating vocals: {res_vocal.stderr}")

        if progress_callback:
            progress_callback("Completed", 0, 0, 100.0)

        dur = self.get_audio_duration_from_ffmpeg(instrumental_path)

        return SeparationResult(
            instrumental_path=instrumental_path,
            vocals_path=vocals_path,
            instrumental_filename=os.path.basename(instrumental_path),
            vocals_filename=os.path.basename(vocals_path),
            duration=dur,
            format=fmt,
        )

    def download_song(
        self,
        info: SongInfo,
        # url: str,
        output_dir: str | Path = "downloads",
        audio_format: str = "mp3",
        keep_m4a: bool = False,
        save_cover: bool = True,
        save_metadata: bool = True,
        progress_callback: Optional[Callable[[str, int, int, float], None]] = None,
    ) -> DownloadResult:
        """
        First i will call a external get req and get the SongInfo obj
        And then i will use this to pass here in this method.

        Downloads, decrypts, and saves the full song as M4A, MP3, or WAV.
        """

        info = info
        song_id = info.base_audio_id

        print(
            "INFO INFO INFO",
            info.model_dump_json(
                indent=2,
                exclude={"prompt", "tags"},
            ),
        )

        # os.makedirs(
        #     output_dir,
        #     exist_ok=True,
        # )
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = get_base_name(info)

        fmt = audio_format.lower().strip()
        if fmt not in SUPPORTED_AUDIO_FORMAT:
            raise ValueError(f"Unsupported audio format: {audio_format}")

        ext = fmt

        # Decrypt and save audio (original M4A, MP3, or WAV)
        # audio_out = os.path.join(output_dir, f"{base_name}.{ext}")
        # m4a_out = os.path.join(output_dir, f"{base_name}.m4a")

        audio_out = output_dir / f"{base_name}.{ext}"
        m4a_out = output_dir / f"{base_name}.m4a"

        stream_url = (
            info.audio_url
            or f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{song_id}.m4a"
        )

        can_reuse_existing = (
            audio_out.exists()
            # os.path.exists(audio_out)
            and audio_out.stat().st_size > 50000
            # and os.path.getsize(audio_out) > 50000
            and (not keep_m4a or ext == "m4a" or m4a_out.exists())
        )

        if can_reuse_existing:
            final_audio_path = audio_out

            if progress_callback:
                progress_callback("Completed", 1, 1, 100.0)
        else:
            print("Song id and stram url is Downloadin,", song_id, stream_url)

            final_audio_path = self.decrypt_and_download(
                song_id=song_id,
                stream_url=stream_url,
                output_audio_path=audio_out,
                audio_format=ext,
                keep_m4a=keep_m4a,
                progress_callback=progress_callback,
            )
            if final_audio_path is None:
                raise RuntimeError("Failed to download and decrypt the audio.")

        m4a_path = m4a_out if ext == "m4a" or keep_m4a else None
        duration = self.get_audio_duration_from_ffmpeg(final_audio_path)

        # Save Cover Art
        cover_path = None
        if save_cover:
            im = download_cover_image(
                info=info,
                destination_folder=output_dir,
            )
            if im:
                print(f"Image has saved into the {im}")
                pass
            else:
                cover_path = None

        # Save Lyrics and Metadata
        metadata_path = None
        if save_metadata:
            meta_path = os.path.join(output_dir, f"{base_name}_info.txt")
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {info.title}\n")
                f.write(f"Suno ID: {info.id}\n")
                f.write(f"Format: {ext.upper()}\n")
                f.write(f"Original Link: {info.audio_url}\n")
                f.write(f"Tags / Style: {info.tags}\n")
                dur_m = int(duration // 60)
                dur_s = int(duration % 60)
                f.write(f"Duration: {dur_m}:{dur_s:02d} ({duration:.1f}s)\n")
                f.write("-" * 50 + "\n")
                f.write("LYRICS / PROMPT:\n")
                f.write(f"{info.prompt or 'Not available'}\n")
            metadata_path = meta_path

        d = DownloadResult(
            info=info,
            audio_path=str(
                final_audio_path
            ),  # TODO i will later pass the full PATH here
            format=ext,
            duration=duration,
            cover_path=cover_path,
            metadata_path=metadata_path,
            m4a_path=str(m4a_path),
        )
        print("DDDDDDDdd", d)
        return d


def launch_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Suno AI Track Downloader, Decryptor and Separator"
    )
    parser.add_argument("url", nargs="?", help="Suno song URL or ID")
    parser.add_argument(
        "-o", "--output", default="downloads", help="Destination folder"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["m4a", "mp3", "wav"],
        default="mp3",
        help="Audio format: m4a (original decrypted stream), mp3 (320kbps), or wav (lossless PCM)",
    )
    parser.add_argument(
        "--no-cover", action="store_true", help="Do not download cover art"
    )
    parser.add_argument(
        "--keep-m4a",
        action="store_true",
        help="Also save the original decrypted M4A when downloading MP3 or WAV",
    )
    parser.add_argument(
        "--sample",
        nargs="?",
        const="auto",
        default=None,
        help="Generate audio sample (e.g., 30, 60, 120 or auto)",
    )
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Download only the direct sample without downloading the full song",
    )
    parser.add_argument(
        "--separate",
        action="store_true",
        help="Separate audio into instrumental and vocal-only tracks",
    )
    parser.add_argument(
        "--gui", action="store_true", help="Open graphical user interface"
    )

    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        launch_gui()
        return

    if not args.url:
        print(
            "Usage: python suno_downloader.py https://suno.com/song/SONG_ID [-f m4a|mp3|wav] [--keep-m4a] [--separate] [--sample 120] [--sample-only]"
        )
        return

    scraper = SunoScraper()

    try:

        def progress_cb(
            stage: str,
            downloaded: int,
            total: int,
            percent: float,
        ):
            if total > 0:
                mb_d = downloaded / (1024 * 1024)
                mb_t = total / (1024 * 1024)
                print(
                    f"\r[{stage.upper()}] [{percent:.1f}%] {mb_d:.2f}MB / {mb_t:.2f}MB",
                    end="",
                )
            else:
                print(f"\r[{stage.upper()}] Processing...", end="")

        if args.sample_only:
            dur_req = None
            if args.sample and args.sample != "auto":
                try:
                    dur_req = float(args.sample)
                except ValueError:
                    dur_req = None
            print(
                f"\n✂️ DIRECTLY downloading sample ({args.format.upper()}) without saving full song: {args.url}"
            )
            sample_res = scraper.download_sample_direct(
                args.url,
                duration_sec=dur_req,
                output_dir=args.output,
                audio_format=args.format,
                save_cover=not args.no_cover,
                progress_callback=progress_cb,
            )
            print(f"\n\n✅ Sample generated without downloading the full song!")
            print(f"🎵 Title: {sample_res.info.title}")
            print(
                f"✂️ Sample duration: {sample_res.actual_sample_duration:.1f}s (Total: {sample_res.total_duration:.1f}s)"
            )
            print(f"🎧 Sample file: {sample_res.sample_path}")
            if sample_res.cover_path:
                print(f"🖼️ Cover: {sample_res.cover_path}")
            return

        print(
            f"\n🎵 Connecting and decrypting Suno song ({args.format.upper()}): {args.url}"
        )
        info = scraper.scrape_song_info(args.url)
        res = scraper.download_song(
            info,
            output_dir=args.output,
            audio_format=args.format,
            keep_m4a=args.keep_m4a,
            save_cover=not args.no_cover,
            progress_callback=progress_cb,
        )
        print(
            f"\n\n✅ Download and decryption completed in "
            f"{args.format.upper()} format!"
        )
        print(f"🎵 Title: {res.info.title}")

        dur_m = int(res.duration // 60)
        dur_s = int(res.duration % 60)
        print(f"⏱️ Total duration: {dur_m}:{dur_s:02d} ({res.duration:.1f}s)")
        print(f"🎧 Audio file ({args.format.upper()}): {res.audio_path}")
        if res.m4a_path and args.format != "m4a":
            print(f"📱 Original M4A: {res.m4a_path}")
        if res.cover_path:
            print(f"🖼️ Cover: {res.cover_path}")
        if res.metadata_path:
            print(f"📄 Lyrics and Metadata: {res.metadata_path}")

        # If a sample was requested via command
        if args.sample:
            dur_req = None
            if args.sample != "auto":
                try:
                    dur_req = float(args.sample)
                except ValueError:
                    dur_req = None
            sample_res = scraper.create_audio_sample(
                res.audio_path, duration_sec=dur_req
            )
            print(
                f"✂️ Sample generated ({sample_res.actual_sample_duration:.1f}s): {sample_res.sample_path}"
            )

        # If track and vocal separation was requested
        if args.separate:
            print("\n🎤 Separating instrumental track and vocals...")
            sep_res = scraper.separate_vocals_and_instrumental(
                res.audio_path, output_format=args.format
            )
            # print(f"🎹 Instrumental Track: {sep_res['instrumental_path']}")
            # print(f"🎙️ Vocals Only (Acapella): {sep_res['vocals_path']}")

            print(f"🎹 Instrumental Track: {sep_res.instrumental_path}")
            print(f"🎙️ Vocals Only (Acapella): {sep_res.vocals_path}")

    except Exception as e:
        print(f"\n❌ Error during download: {e}")


def launch_gui():
    """
    Launches the Tkinter graphical user interface.

    #TODO For now i will not touch this function
    i want my cli to work first properly then come to check this later
    """
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import threading
    from PIL import Image, ImageTk

    root = tk.Tk()
    root.title("Suno AI Song Downloader & Decryptor HQ (MP3 / WAV & Stems)")
    root.geometry("740x860")
    root.minsize(680, 750)
    root.configure(bg="#121214")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "TProgressbar", thickness=10, troughcolor="#202024", background="#7928CA"
    )
    style.configure(
        "TCombobox",
        fieldbackground="#202024",
        background="#29292E",
        foreground="#FFFFFF",
    )

    scraper = SunoScraper()
    last_audio_file = [None]
    last_sample_file = [None]
    last_inst_file = [None]
    last_vocal_file = [None]
    current_duration = [0.0]

    # Header
    header_frame = tk.Frame(root, bg="#1a1a1e", height=70)
    header_frame.pack(fill="x", side="top")
    header_frame.pack_propagate(False)

    lbl_title = tk.Label(
        header_frame,
        text="⚡ SUNO AI DOWNLOADER HQ",
        font=("Segoe UI", 16, "bold"),
        fg="#FF0080",
        bg="#1a1a1e",
    )
    lbl_title.pack(side="left", padx=20, pady=15)

    lbl_sub = tk.Label(
        header_frame,
        text="MP3 / WAV Download + Track and Vocal Separator",
        font=("Segoe UI", 10, "italic"),
        fg="#888899",
        bg="#1a1a1e",
    )
    lbl_sub.pack(side="left", pady=18)

    # Main Container
    main_frame = tk.Frame(root, bg="#121214")
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # URL Input Section
    lbl_url = tk.Label(
        main_frame,
        text="Paste the shared Suno link (e.g. https://suno.com/song/...):",
        font=("Segoe UI", 10, "bold"),
        fg="#E1E1E6",
        bg="#121214",
    )
    lbl_url.pack(anchor="w", pady=(0, 4))

    url_entry_frame = tk.Frame(main_frame, bg="#202024", bd=1, relief="flat")
    url_entry_frame.pack(fill="x", pady=(0, 8))

    url_entry = tk.Entry(
        url_entry_frame,
        font=("Segoe UI", 11),
        bg="#202024",
        fg="#FFFFFF",
        insertbackground="#FF0080",
        relief="flat",
    )
    url_entry.pack(fill="x", padx=10, pady=8)

    # Options & Format Frame
    opts_frame = tk.Frame(main_frame, bg="#121214")
    opts_frame.pack(fill="x", pady=(0, 6))

    var_format = tk.StringVar(value="mp3")
    lbl_fmt = tk.Label(
        opts_frame,
        text="Formato:",
        font=("Segoe UI", 9, "bold"),
        fg="#00DFD8",
        bg="#121214",
    )
    lbl_fmt.pack(side="left", padx=(0, 6))

    rad_mp3 = tk.Radiobutton(
        opts_frame,
        text="MP3 (320 kbps)",
        variable=var_format,
        value="mp3",
        bg="#121214",
        fg="#FFFFFF",
        selectcolor="#202024",
        activebackground="#121214",
        activeforeground="#FFFFFF",
        font=("Segoe UI", 9, "bold"),
    )
    rad_mp3.pack(side="left", padx=(0, 10))

    rad_wav = tk.Radiobutton(
        opts_frame,
        text="WAV (Lossless PCM)",
        variable=var_format,
        value="wav",
        bg="#121214",
        fg="#00DFD8",
        selectcolor="#202024",
        activebackground="#121214",
        activeforeground="#00DFD8",
        font=("Segoe UI", 9, "bold"),
    )
    rad_wav.pack(side="left", padx=(0, 20))

    var_cover = tk.BooleanVar(value=True)
    var_meta = tk.BooleanVar(value=True)

    chk_cover = tk.Checkbutton(
        opts_frame,
        text="Portada",
        variable=var_cover,
        bg="#121214",
        fg="#A8A8B3",
        selectcolor="#202024",
        activebackground="#121214",
        activeforeground="#FFFFFF",
        font=("Segoe UI", 9),
    )
    chk_cover.pack(side="left", padx=(0, 12))

    chk_meta = tk.Checkbutton(
        opts_frame,
        text="Lyrics (.txt)",
        variable=var_meta,
        bg="#121214",
        fg="#A8A8B3",
        selectcolor="#202024",
        activebackground="#121214",
        activeforeground="#FFFFFF",
        font=("Segoe UI", 9),
    )
    chk_meta.pack(side="left")

    # Folder Selector Frame
    folder_frame = tk.Frame(main_frame, bg="#121214")
    folder_frame.pack(fill="x", pady=(0, 8))

    lbl_folder_text = tk.Label(
        folder_frame,
        text="Carpeta de destino:",
        font=("Segoe UI", 9),
        fg="#A8A8B3",
        bg="#121214",
    )
    lbl_folder_text.pack(side="left")

    default_dir = os.path.abspath("downloads")
    selected_dir_var = tk.StringVar(value=default_dir)

    lbl_folder_path = tk.Label(
        folder_frame,
        textvariable=selected_dir_var,
        font=("Segoe UI", 9, "italic"),
        fg="#00DFD8",
        bg="#121214",
    )
    lbl_folder_path.pack(side="left", padx=10)

    def choose_directory():
        d = filedialog.askdirectory(initialdir=selected_dir_var.get())
        if d:
            selected_dir_var.set(d)

    btn_browse = tk.Button(
        folder_frame,
        text="Examinar...",
        command=choose_directory,
        bg="#29292E",
        fg="#E1E1E6",
        relief="flat",
        font=("Segoe UI", 8, "bold"),
        padx=8,
        pady=2,
        cursor="hand2",
    )
    btn_browse.pack(side="right")

    # Progress Section
    progress_bar = ttk.Progressbar(main_frame, style="TProgressbar", mode="determinate")
    progress_bar.pack(fill="x", pady=(0, 4))

    status_var = tk.StringVar(
        value="Ready. Paste a Suno link and press 'Download Song'."
    )
    lbl_status = tk.Label(
        main_frame,
        textvariable=status_var,
        font=("Segoe UI", 9),
        fg="#A8A8B3",
        bg="#121214",
    )
    lbl_status.pack(anchor="w", pady=(0, 6))

    # Song Info Preview Box
    info_card = tk.Frame(main_frame, bg="#1a1a1e", bd=1, relief="flat")
    info_card.pack(fill="x", pady=(0, 8))

    cover_label = tk.Label(
        info_card, bg="#202024", width=12, height=6, text="[Portada]", fg="#666677"
    )
    cover_label.pack(side="left", padx=10, pady=8)

    details_frame = tk.Frame(info_card, bg="#1a1a1e")
    details_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=8)

    lbl_song_title = tk.Label(
        details_frame,
        text="Title: --",
        font=("Segoe UI", 11, "bold"),
        fg="#FFFFFF",
        bg="#1a1a1e",
        anchor="w",
    )
    lbl_song_title.pack(fill="x")

    lbl_song_meta = tk.Label(
        details_frame,
        text="Style: -- | Duration: --",
        font=("Segoe UI", 9),
        fg="#FF0080",
        bg="#1a1a1e",
        anchor="w",
    )
    lbl_song_meta.pack(fill="x", pady=(2, 4))

    txt_lyrics = tk.Text(
        details_frame,
        height=3,
        font=("Consolas", 8),
        bg="#121214",
        fg="#CCCCCC",
        relief="flat",
        bd=0,
    )
    txt_lyrics.pack(fill="x", expand=True)
    txt_lyrics.insert("1.0", "Lyrics / prompt will appear here...")
    txt_lyrics.config(state="disabled")

    # Sample Controls Frame (Audio Samples)
    sample_box = tk.LabelFrame(
        main_frame,
        text=" ✂️ AUDIO SAMPLE (PREVIEW - DIRECT WITHOUT FULL DOWNLOAD) ",
        font=("Segoe UI", 9, "bold"),
        fg="#00DFD8",
        bg="#18181c",
        bd=1,
        relief="groove",
    )
    sample_box.pack(fill="x", pady=(0, 8), padx=2, ipady=3)

    sample_inner = tk.Frame(sample_box, bg="#18181c")
    sample_inner.pack(fill="x", padx=10, pady=3)

    lbl_sample_opt = tk.Label(
        sample_inner, text="Duration:", font=("Segoe UI", 9), fg="#E1E1E6", bg="#18181c"
    )
    lbl_sample_opt.pack(side="left", padx=(0, 6))

    sample_options = [
        "⚡ 30 Seconds",
        "⏱️ 1 Minute (60s)",
        "⏳ 2 Minutes (120s)",
        "🌓 Half the Song (50%)",
        "✨ Auto (Recommended)",
    ]
    sample_choice_var = tk.StringVar(value="✨ Auto (Recommended)")
    sample_combo = ttk.Combobox(
        sample_inner,
        textvariable=sample_choice_var,
        values=sample_options,
        state="readonly",
        width=20,
    )
    sample_combo.pack(side="left", padx=(0, 8))

    def generate_sample_action():
        url = url_entry.get().strip()
        has_full_download = bool(
            last_audio_file[0] and os.path.exists(last_audio_file[0])
        )

        if not has_full_download and not url:
            messagebox.showwarning(
                "Link Required",
                "Please paste the Suno song link in the box above to generate a sample.",
            )
            url_entry.focus_set()
            return

        choice = sample_choice_var.get()
        dur = None
        tot = current_duration[0] or (
            scraper.get_audio_duration_from_ffmpeg(last_audio_file[0])
            if has_full_download
            else 0.0
        )

        if "30" in choice:
            dur = 30.0
        elif "1 Minute" in choice or "60s" in choice:
            dur = 60.0
        elif "2 Minutes" in choice or "120s" in choice:
            dur = 120.0
        elif "Half" in choice:
            dur = (
                "half"
                if not has_full_download
                else (max(15.0, tot * 0.5) if tot > 0 else 60.0)
            )
        else:
            dur = None
            # auto

        status_var.set("Preparing audio sample...")
        progress_bar["value"] = 15
        btn_sample_create.config(state="disabled", text="⏳ Creating...")
        btn_download.config(state="disabled")

        def sample_task():
            try:
                if has_full_download:
                    status_var.set("Generating sample from the downloaded file...")
                    s_res = scraper.create_audio_sample(
                        last_audio_file[0],
                        duration_sec=dur if isinstance(dur, (int, float)) else None,
                    )
                else:

                    def on_sample_progress(stage, downloaded, total, percent):
                        progress_bar["value"] = percent
                        if total > 0:
                            mb_d = downloaded / (1024 * 1024)
                            mb_t = total / (1024 * 1024)
                            status_var.set(
                                f"[Sample: {stage.capitalize()}] {percent:.1f}% ({mb_d:.2f}MB / {mb_t:.2f}MB)"
                            )
                        else:
                            status_var.set(f"[Sample] {stage.capitalize()}...")

                    s_res = scraper.download_sample_direct(
                        url,
                        duration_sec=dur,
                        output_dir=selected_dir_var.get(),
                        audio_format=var_format.get(),
                        save_cover=var_cover.get(),
                        progress_callback=on_sample_progress,
                    )

                    # Update song info card
                    info = (
                        s_res.info if isinstance(s_res, SampleDownloadResult) else None
                    )
                    if info:
                        lbl_song_title.config(text=f"🎵 {info.title}")
                        tot_dur = s_res.total_duration
                        dur_m = int(tot_dur // 60)
                        dur_s = int(tot_dur % 60)
                        fmt_label = var_format.get().upper()
                        lbl_song_meta.config(
                            text=f"🏷️ {info.tags or 'No style'}  |  ⏱️ Total: {dur_m}:{dur_s:02d}  |  ✂️ Sample: {s_res.actual_sample_duration:.1f}s  |  💿 {fmt_label}"
                        )
                        current_duration[0] = tot_dur

                        txt_lyrics.config(state="normal")
                        txt_lyrics.delete("1.0", "end")
                        txt_lyrics.insert("1.0", info.prompt or "No lyrics available.")
                        txt_lyrics.config(state="disabled")

                        cover_path = s_res.cover_path
                        if cover_path and os.path.exists(cover_path):
                            try:
                                img = Image.open(cover_path)
                                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                                tk_img = ImageTk.PhotoImage(img)
                                cover_label.config(image=tk_img, text="")
                                cover_label.image = tk_img
                            except Exception:
                                pass

                last_sample_file[0] = s_res.sample_path
                progress_bar["value"] = 100
                status_var.set(
                    f"✅ Sample ({s_res.actual_sample_duration:.1f}s) saved successfully! ({os.path.basename(s_res.sample_path)})"
                )
                btn_sample_play.config(state="normal", text="▶️ Play Sample")
                sample_title = (
                    s_res.info.title
                    if isinstance(s_res, SampleDownloadResult)
                    else os.path.basename(s_res.sample_path)
                )
                messagebox.showinfo(
                    "Sample Created Successfully!",
                    f"Sample generated without downloading the full song:\n\n"
                    f"🎵 Title: {sample_title}\n"
                    f"⏱️ Sample duration: {s_res.actual_sample_duration:.1f}s\n"
                    f"🎧 File: {os.path.basename(s_res.sample_path)}\n"
                    f"📂 Location:\n{s_res.sample_path}",
                )
            except Exception as e:
                status_var.set(f"❌ Error creating sample: {str(e)}")
                messagebox.showerror(
                    "Sample Error", f"The sample could not be created:\n\n{str(e)}"
                )
            finally:
                progress_bar["value"] = 0
                btn_sample_create.config(state="normal", text="✂️ Download Sample")
                btn_download.config(state="normal")

        threading.Thread(target=sample_task, daemon=True).start()

    btn_sample_create = tk.Button(
        sample_inner,
        text="✂️ Download Sample",
        command=generate_sample_action,
        bg="#00DFD8",
        fg="#000000",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=8,
        pady=2,
        state="normal",
        cursor="hand2",
    )
    btn_sample_create.pack(side="left", padx=(0, 6))

    def play_sample_audio():
        if last_sample_file[0] and os.path.exists(last_sample_file[0]):
            os.startfile(last_sample_file[0])

    btn_sample_play = tk.Button(
        sample_inner,
        text="▶️ Reproducir",
        command=play_sample_audio,
        bg="#29292E",
        fg="#00DFD8",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=6,
        pady=2,
        state="disabled",
        cursor="hand2",
    )
    btn_sample_play.pack(side="left")

    # 🎤 Stem Separation Frame (Track and Vocal Separator)
    stem_box = tk.LabelFrame(
        main_frame,
        text=" 🎤 TRACK AND VOCAL SEPARATOR (STEMS) ",
        font=("Segoe UI", 9, "bold"),
        fg="#FF0080",
        bg="#18181c",
        bd=1,
        relief="groove",
    )
    stem_box.pack(fill="x", pady=(0, 8), padx=2, ipady=3)

    stem_inner = tk.Frame(stem_box, bg="#18181c")
    stem_inner.pack(fill="x", padx=10, pady=3)

    lbl_stem_desc = tk.Label(
        stem_inner,
        text="Isolate the instrumental and vocal/acapella into separate tracks:",
        font=("Segoe UI", 8),
        fg="#A8A8B3",
        bg="#18181c",
    )
    lbl_stem_desc.pack(anchor="w", pady=(0, 4))

    stem_btn_row = tk.Frame(stem_inner, bg="#18181c")
    stem_btn_row.pack(fill="x")

    def separate_stems_action():
        if not last_audio_file[0] or not os.path.exists(last_audio_file[0]):
            messagebox.showwarning(
                "Download the Song First",
                "You must download a song before separating the track and vocals.",
            )
            return

        status_var.set(
            "Separating instrumental track and vocals with high-fidelity DSP filters..."
        )
        btn_stem_separate.config(state="disabled", text="⏳ Separating...")

        def stem_task():
            try:
                sep_res = scraper.separate_vocals_and_instrumental(
                    last_audio_file[0], output_format=var_format.get()
                )
                # last_inst_file[0] = sep_res["instrumental_path"]
                # last_vocal_file[0] = sep_res["vocals_path"]
                last_inst_file[0] = sep_res.instrumental_path
                last_vocal_file[0] = sep_res.vocals_path
                status_var.set(
                    "✅ Instrumental track and vocals separated successfully!"
                )
                btn_play_inst.config(state="normal")
                btn_play_vocal.config(state="normal")
                messagebox.showinfo(
                    "Separation Successful",
                    f"Tracks generated!\n\n🎹 Instrumental:\n{sep_res.instrumental_filename}\n\n🎙️ Vocals Only:\n{sep_res.vocals_filename}",
                )

            except Exception as e:
                status_var.set(f"❌ Error separating: {str(e)}")
                messagebox.showerror(
                    "Error", f"The audio could not be separated: {str(e)}"
                )

            finally:
                btn_stem_separate.config(
                    state="normal", text="✨ Separate Track and Vocals"
                )

        threading.Thread(target=stem_task, daemon=True).start()

    btn_stem_separate = tk.Button(
        stem_btn_row,
        text="✨ Separate Track and Vocals",
        command=separate_stems_action,
        bg="#FF0080",
        fg="#FFFFFF",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        state="disabled",
        cursor="hand2",
    )
    btn_stem_separate.pack(side="left", padx=(0, 8))

    def play_inst_audio():
        if last_inst_file[0] and os.path.exists(last_inst_file[0]):
            os.startfile(last_inst_file[0])

    btn_play_inst = tk.Button(
        stem_btn_row,
        text="🎹 Instrumental Track",
        command=play_inst_audio,
        bg="#29292E",
        fg="#00DFD8",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=8,
        pady=3,
        state="disabled",
        cursor="hand2",
    )
    btn_play_inst.pack(side="left", padx=(0, 6))

    def play_vocal_audio():
        if last_vocal_file[0] and os.path.exists(last_vocal_file[0]):
            os.startfile(last_vocal_file[0])

    btn_play_vocal = tk.Button(
        stem_btn_row,
        text="🎙️ Vocals Only",
        command=play_vocal_audio,
        bg="#29292E",
        fg="#FF0080",
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=8,
        pady=3,
        state="disabled",
        cursor="hand2",
    )
    btn_play_vocal.pack(side="left")

    # Action Buttons Frame
    btn_frame = tk.Frame(main_frame, bg="#121214")
    btn_frame.pack(fill="x", pady=(4, 0))

    def set_ui_loading(is_loading: bool):
        if is_loading:
            btn_download.config(
                state="disabled", text="⏳ Decrypting and Downloading..."
            )
            btn_paste.config(state="disabled")
            btn_sample_create.config(state="disabled")
            btn_stem_separate.config(state="disabled")
        else:
            btn_download.config(state="normal", text="🚀 DOWNLOAD SONG")
            btn_paste.config(state="normal")
            btn_sample_create.config(state="normal")
            if last_audio_file[0] and os.path.exists(last_audio_file[0]):
                btn_stem_separate.config(state="normal")

    def run_download_thread():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL Required", "Please paste the shared Suno link.")
            return

        set_ui_loading(True)
        progress_bar["value"] = 0
        status_var.set("Connecting and retrieving the audio license...")

        def task():
            try:

                def on_progress(stage, downloaded, total, percent):
                    progress_bar["value"] = percent
                    if total > 0:
                        mb_d = downloaded / (1024 * 1024)
                        mb_t = total / (1024 * 1024)
                        status_var.set(
                            f"[{stage.capitalize()}] {percent:.1f}% ({mb_d:.2f} MB / {mb_t:.2f} MB)"
                        )
                    else:
                        status_var.set(f"Processing: {stage}...")

                chosen_fmt = var_format.get()
                info = scraper.scrape_song_info(url)
                res = scraper.download_song(
                    info,
                    output_dir=selected_dir_var.get(),
                    audio_format=chosen_fmt,
                    save_cover=var_cover.get(),
                    save_metadata=var_meta.get(),
                    progress_callback=on_progress,
                )

                info = res.info
                last_audio_file[0] = res.audio_path
                current_duration[0] = res.duration

                lbl_song_title.config(text=f"🎵 {info.title}")
                dur_m = int(res.duration // 60)
                dur_s = int(res.duration % 60)
                lbl_song_meta.config(
                    text=f"🏷️ {info.tags or 'No style'}  |  ⏱️ {dur_m}:{dur_s:02d}  |  💿 {chosen_fmt.upper()}"
                )

                txt_lyrics.config(state="normal")
                txt_lyrics.delete("1.0", "end")
                lyrics_text = info.prompt or "No lyrics available."
                txt_lyrics.insert("1.0", lyrics_text)
                txt_lyrics.config(state="disabled")

                if res.cover_path and os.path.exists(res.cover_path):
                    try:
                        img = Image.open(res.cover_path)
                        img = img.resize((100, 100), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                        cover_label.config(image=tk_img, text="")
                        cover_label.image = tk_img
                    except Exception:
                        pass

                progress_bar["value"] = 100
                status_var.set(
                    f"✅ {chosen_fmt.upper()} downloaded successfully! ({os.path.basename(res.audio_path)})"
                )
                btn_play.config(state="normal", text=f"▶️ Play {chosen_fmt.upper()}")
                btn_sample_create.config(state="normal")
                btn_stem_separate.config(state="normal")
                messagebox.showinfo(
                    "Download Successful!",
                    f"{chosen_fmt.upper()} song ready:\n\n{info.title}\nDuration: {dur_m}:{dur_s:02d}\n\nLocation:\n{res.audio_path}",
                )

            except Exception as e:
                status_var.set(f"❌ Error: {str(e)}")
                messagebox.showerror(
                    "Download Error",
                    f"An error occurred while processing the link:\n\n{str(e)}",
                )
            finally:
                set_ui_loading(False)

        threading.Thread(target=task, daemon=True).start()

    def paste_clipboard():
        try:
            cb = root.clipboard_get().strip()
            if cb:
                url_entry.delete(0, tk.END)
                url_entry.insert(0, cb)
        except Exception:
            pass

    btn_paste = tk.Button(
        btn_frame,
        text="📋 Pegar",
        command=paste_clipboard,
        bg="#29292E",
        fg="#FFFFFF",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padx=10,
        pady=8,
        cursor="hand2",
    )
    btn_paste.pack(side="left", padx=(0, 8))

    btn_download = tk.Button(
        btn_frame,
        text="🚀 DOWNLOAD SONG",
        command=run_download_thread,
        bg="#7928CA",
        fg="#FFFFFF",
        activebackground="#FF0080",
        activeforeground="#FFFFFF",
        relief="flat",
        font=("Segoe UI", 11, "bold"),
        pady=8,
        cursor="hand2",
    )
    btn_download.pack(side="left", fill="x", expand=True)

    def play_downloaded_audio():
        if last_audio_file[0] and os.path.exists(last_audio_file[0]):
            os.startfile(last_audio_file[0])
        else:
            open_downloads_folder()

    btn_play = tk.Button(
        btn_frame,
        text="▶️ Play",
        command=play_downloaded_audio,
        bg="#00DFD8",
        fg="#000000",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padx=8,
        pady=8,
        state="disabled",
        cursor="hand2",
    )
    btn_play.pack(side="left", padx=(8, 0))

    def open_downloads_folder():
        folder = selected_dir_var.get()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    btn_open_folder = tk.Button(
        btn_frame,
        text="📂 Folder",
        command=open_downloads_folder,
        bg="#202024",
        fg="#A8A8B3",
        relief="flat",
        font=("Segoe UI", 10),
        padx=8,
        pady=8,
        cursor="hand2",
    )
    btn_open_folder.pack(side="right", padx=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    launch_cli()
