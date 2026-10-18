"""
main.py

# Entry point for cloud deployment (Render, Railway, Hugging Face, etc.)
"""

import os
import uvicorn
from app.features.suno_mobile_server import app  # type: ignore This need for import here
from app.features.suno_mobile_server import get_local_ip
from app.config import settings


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.app.port))
    print(f"📱 Open on phone: http://{get_local_ip()}:{port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
    )
