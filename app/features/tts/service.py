"""
app/features/tts/service.py

"""

from pathlib import Path
import uuid


import edge_tts

#


AUDIO_CREATE_DIR = Path("downloads") / "audio_create"

voice_agent = "en-IN-NeerjaExpressiveNeural"
# voice_agent = "bn-IN-TanishaaNeural"


async def text_to_speech(
    text: str,
    user_id: int,
    voice: str = voice_agent,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    user_dir = AUDIO_CREATE_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    out_path = user_dir / f"tts_{uuid.uuid4().hex[:8]}.mp3"
    communicate = edge_tts.Communicate(
        text, voice, rate=rate, volume=volume, pitch=pitch
    )
    await communicate.save(str(out_path))
    return out_path
