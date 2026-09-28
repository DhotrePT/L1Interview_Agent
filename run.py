"""Start the L1 Interview Agent.

    python run.py

Then open http://localhost:8000 in Chrome or Edge (camera, microphone and speech
recognition need a Chromium browser on localhost or an https origin).
"""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD")),
    )
