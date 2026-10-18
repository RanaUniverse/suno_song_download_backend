"""
suno_downloader.py

# Mobile Web Server for Suno AI Downloader
# Allows using the application from any mobile phone (Android / iOS) or PC web browser.
# Supports preview / playback, 320 kbps MP3 download, WAV Lossless, and Track/Vocal Separation.

"""

import os
import sys
import socket
import urllib.parse
import time
import asyncio
from typing import (
    Optional,
    # Dict,
    # Any,
    # List,
)
import qrcode
import uvicorn
from fastapi import (
    FastAPI,
    # Request,
    HTTPException,
    Request,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    FileResponse,
    JSONResponse,
)

# from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Import the audio download and processing engine
from app.features.suno_downloader import (
    SunoScraper,
    # sanitize_filename,
)
from app.config import settings

# Ensure UTF-8 in Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = FastAPI(title="Suno AI Mobile & Web Downloader HQ")


# Allow your local VS Code frontend to access the backend API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(
    directory="templates",
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

scraper = SunoScraper()
DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def cleanup_old_files(max_age_seconds: int = 300, max_folder_mb: int = 150):
    """
    Removes files from DOWNLOADS_DIR:
    1. Files older than max_age_seconds (5 minutes / 300s by default).
    2. If the total folder size exceeds max_folder_mb (150 MB), removes the oldest files
       until it reaches a safe size (< 80 MB), avoiding exhaustion of Render's 512 MB limit.
    """
    try:
        if not os.path.exists(DOWNLOADS_DIR):
            return
        now = time.time()
        file_list = []
        total_size = 0
        for f in os.listdir(DOWNLOADS_DIR):
            full_path = os.path.join(DOWNLOADS_DIR, f)
            if os.path.isfile(full_path):
                try:
                    stat = os.stat(full_path)
                    age = now - stat.st_mtime
                    size = stat.st_size
                    if age > max_age_seconds:
                        try:
                            os.remove(full_path)
                            continue
                        except Exception:
                            pass
                    file_list.append((stat.st_mtime, size, full_path))
                    total_size += size
                except Exception:
                    pass

        max_bytes = max_folder_mb * 1024 * 1024
        target_bytes = 80 * 1024 * 1024
        if total_size > max_bytes:
            file_list.sort(key=lambda x: x[0])
            for _, size, path in file_list:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        total_size -= size
                        if total_size <= target_bytes:
                            break
                except Exception:
                    pass
    except Exception:
        pass


async def delayed_remove_file(file_path: str, delay_sec: int = 300):
    """Waits delay_sec seconds (5 min by default), then removes the file to free Render space."""
    await asyncio.sleep(delay_sec)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


@app.on_event("startup")
async def start_periodic_cleanup():
    """Cleans old files at startup and runs cleanup every 60 seconds in the background."""
    cleanup_old_files(max_age_seconds=300)

    async def loop():
        while True:
            await asyncio.sleep(60)
            cleanup_old_files(max_age_seconds=300)

    asyncio.create_task(loop())


def get_local_ip() -> str:
    """Detects the computer's local IP on the Wi-Fi network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


class DownloadRequest(BaseModel):
    url: str
    format: Optional[str] = "mp3"


class SampleRequest(BaseModel):
    filename: str
    duration_sec: Optional[float] = None
    start_sec: Optional[float] = 0.0
    preset: Optional[str] = None


class SeparateRequest(BaseModel):
    filename: str
    format: Optional[str] = "mp3"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.post("/api/download")
async def api_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        url = req.url.strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL required")

        fmt = (req.format or "mp3").lower().strip()
        if fmt not in {"m4a", "mp3", "wav"}:
            raise HTTPException(
                status_code=400, detail="Format must be m4a, mp3, or wav"
            )
        info = scraper.scrape_song_info(url)
        res = scraper.download_song(
            info,
            output_dir=DOWNLOADS_DIR,
            audio_format=fmt,
        )
        info = res.info
        audio_file = os.path.basename(res.audio_path)
        duration = res.duration
        dur_m = int(duration // 60)
        dur_s = int(duration % 60)
        duration_formatted = f"{dur_m}:{dur_s:02d}"

        # Suggested calculation for the sample
        suggested_sec = 60
        if duration <= 60:
            suggested_sec = 30
        elif duration > 180:
            suggested_sec = 120
        suggested_formatted = (
            f"{int(suggested_sec // 60)} min"
            if suggested_sec >= 60
            else f"{int(suggested_sec)} sec"
        )

        cover_url = ""
        if res.cover_path and os.path.exists(res.cover_path):
            cover_file = os.path.basename(res.cover_path)
            cover_url = f"/downloads/{urllib.parse.quote(cover_file)}"
        elif info.image_url:
            cover_url = info.image_url

        # Schedule auto-deletion in 5 minutes (300s) to avoid taking up disk space on the server
        background_tasks.add_task(delayed_remove_file, res.audio_path, 300)
        if res.cover_path:
            background_tasks.add_task(delayed_remove_file, res.cover_path, 300)
        if res.metadata_path:
            background_tasks.add_task(delayed_remove_file, res.metadata_path, 300)

        return {
            "success": True,
            "title": info.title,
            "tags": info.tags,
            "filename": audio_file,
            "format": res.format,
            "download_url": f"/downloads/{urllib.parse.quote(audio_file)}",
            "cover_url": cover_url,
            "duration_seconds": duration,
            "duration_formatted": duration_formatted,
            "suggested_sample_seconds": suggested_sec,
            "suggested_sample_formatted": suggested_formatted,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/separate")
async def api_separate_stems(req: SeparateRequest, background_tasks: BackgroundTasks):
    """Separates the song into Instrumental Track and Vocals Only."""
    try:
        filename = req.filename.strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Filename required")

        input_path = os.path.join(DOWNLOADS_DIR, filename)
        if not os.path.exists(input_path):
            raise HTTPException(
                status_code=404, detail="The file does not exist in downloads"
            )

        fmt = (
            (
                req.format
                or (
                    "wav"
                    if filename.lower().endswith(".wav")
                    else "m4a" if filename.lower().endswith(".m4a") else "mp3"
                )
            )
            .lower()
            .strip()
        )

        sep_res = scraper.separate_vocals_and_instrumental(
            input_audio=input_path, output_dir=DOWNLOADS_DIR, output_format=fmt
        )

        inst_file = sep_res["instrumental_filename"]
        vocal_file = sep_res["vocals_filename"]

        # Schedule auto-deletion in 5 minutes (300s)
        if sep_res.get("instrumental_path"):
            background_tasks.add_task(
                delayed_remove_file, sep_res["instrumental_path"], 300
            )
        if sep_res.get("vocals_path"):
            background_tasks.add_task(delayed_remove_file, sep_res["vocals_path"], 300)

        return {
            "success": True,
            "instrumental_filename": inst_file,
            "instrumental_url": f"/downloads/{urllib.parse.quote(inst_file)}",
            "vocals_filename": vocal_file,
            "vocals_url": f"/downloads/{urllib.parse.quote(vocal_file)}",
            "duration": sep_res.get("duration", 0.0),
            "format": fmt,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/sample")
async def api_generate_sample(req: SampleRequest, background_tasks: BackgroundTasks):
    """Generates a sample/preview from an existing song."""
    try:
        filename = req.filename.strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Filename required")

        input_path = os.path.join(DOWNLOADS_DIR, filename)
        if not os.path.exists(input_path):
            raise HTTPException(
                status_code=404, detail="The source file does not exist in downloads"
            )

        total_dur = scraper.get_audio_duration(input_path)
        duration_sec = req.duration_sec
        preset = (req.preset or "").lower()

        if preset == "30s":
            duration_sec = 30.0
        elif preset in ("60s", "1m"):
            duration_sec = 60.0
        elif preset in ("120s", "2m"):
            duration_sec = 120.0
        elif preset in ("half", "50%"):
            duration_sec = max(15.0, total_dur * 0.5) if total_dur > 0 else 60.0
        elif preset == "auto":
            duration_sec = None

        sample_res = scraper.create_audio_sample(
            input_mp3=input_path,
            duration_sec=duration_sec,
            start_sec=req.start_sec or 0.0,
            apply_fade=True,
        )

        sample_filename = sample_res.filename
        # Schedule auto-deletion in 5 minutes (300s)
        background_tasks.add_task(delayed_remove_file, sample_res.sample_path, 300)

        return {
            "success": True,
            "filename": sample_filename,
            "sample_url": f"/downloads/{urllib.parse.quote(sample_filename)}",
            "sample_duration": sample_res.actual_sample_duration,
            "total_duration": sample_res.total_duration,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/downloads/{filename}")
async def download_file_endpoint(filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "application/octet-stream"
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif filename.endswith(".wav"):
        media_type = "audio/wav"
    elif filename.endswith(".m4a"):
        media_type = "audio/mp4"
    elif filename.endswith(".jpeg") or filename.endswith(".jpg"):
        media_type = "image/jpeg"
    elif filename.endswith(".png"):
        media_type = "image/png"
    elif filename.endswith(".txt"):
        media_type = "text/plain; charset=utf-8"

    # Upon being downloaded or played, schedule deletion in 2 minutes (120s)
    # so that transmission finishes and server space is then freed up
    background_tasks.add_task(delayed_remove_file, file_path, 120)

    return FileResponse(file_path, media_type=media_type, filename=filename)


@app.get("/api/files")
async def list_downloaded_files():
    files = []
    if os.path.exists(DOWNLOADS_DIR):
        file_entries = []
        for f in os.listdir(DOWNLOADS_DIR):
            if f.endswith((".m4a", ".mp3", ".wav")):
                full_path = os.path.join(DOWNLOADS_DIR, f)
                mtime = os.path.getmtime(full_path)
                file_entries.append((mtime, f))

        file_entries.sort(key=lambda x: x[0], reverse=True)
        for _, f in file_entries[:30]:
            clean_name = f.rsplit(".", 1)[0]
            files.append({"filename": f, "name": clean_name})
    return files


def run_server():
    local_ip = get_local_ip()
    port = 8000
    mobile_url = f"http://{local_ip}:{port}"

    print("\n" + "=" * 58)
    print(" 🚀 SUNO AI MOBILE SERVER ACTIVATED (HQ)")
    print("=" * 58)
    print(f"\n📲 OPEN THIS LINK IN YOUR PHONE'S BROWSER:\n")
    print(f"👉 \033[92m{mobile_url}\033[0m\n")
    print("=" * 58)
    print("📷 OR SCAN THIS QR CODE WITH YOUR PHONE'S CAMERA:")
    print("=" * 58 + "\n")

    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception:
        pass

    print("\n" + "-" * 58)
    print("💡 Make sure your phone is connected to the same Wi-Fi network.")
    print("Press Ctrl + C in this window to stop the server.")
    print("-" * 58 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
