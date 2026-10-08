"""
main.py

# Entry point for cloud deployment (Render, Railway, Hugging Face, etc.)
"""

import os
import uvicorn
from app.features.suno_mobile_server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
