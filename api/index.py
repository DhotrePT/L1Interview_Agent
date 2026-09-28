"""Vercel serverless entrypoint.

Vercel serves every request through this module. The repo root is not on
sys.path inside the function bundle, so put it there before importing the app.

Read the persistence warning in vercel.json before relying on this for a real
interview - on Vercel the session store lives in /tmp, which is per-instance
and temporary.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402  (path setup must run first)

__all__ = ["app"]
