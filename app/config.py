"""Runtime configuration, read once at import time."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Where interview sessions are stored. Override with DATA_DIR when the app runs
# on a host whose app directory is read-only, and point it at a mounted disk -
# sessions and recordings must survive a restart.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data" / "sessions")))
STATIC_DIR = BASE_DIR / "static"

# Candidate code runs in a temp folder next to the app, not in the system temp
# directory - keeps the system drive out of the picture entirely.
RUN_TMP_DIR = Path(os.getenv("RUN_TMP_DIR", str(BASE_DIR / "data" / "tmp")))

INTERVIEW_MINUTES = int(os.getenv("INTERVIEW_MINUTES", "30"))
INTERVIEW_SECONDS = INTERVIEW_MINUTES * 60

SCORING_MODEL = os.getenv("SCORING_MODEL", "claude-opus-5")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Empty list means "any syntactically valid email may log in".
ALLOWED_EMAIL_DOMAINS = [
    d.strip().lower().lstrip("@")
    for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
    if d.strip()
]

# --- Proctoring -------------------------------------------------------------
# Suspicious events (tab switch, leaving fullscreen, paste, devtools keys...).
# At ALARM_AT the candidate gets a full-screen alarm; at TERMINATE_AT the
# interview ends automatically and the attempt is flagged.
PROCTOR_ALARM_AT = int(os.getenv("PROCTOR_ALARM_AT", "3"))
PROCTOR_TERMINATE_AT = int(os.getenv("PROCTOR_TERMINATE_AT", "6"))

# May a candidate interview twice for the same post?
ALLOW_RETAKE = os.getenv("ALLOW_RETAKE", "false").strip().lower() in {"1", "true", "yes"}

# How long candidate code may run in the "Run code" sandbox.
CODE_RUN_TIMEOUT_SECONDS = int(os.getenv("CODE_RUN_TIMEOUT_SECONDS", "8"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
RUN_TMP_DIR.mkdir(parents=True, exist_ok=True)
