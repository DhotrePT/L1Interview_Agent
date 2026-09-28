"""File-backed session store.

One folder per interview session:

    data/sessions/<session_id>/
        session.json     candidate, questions, answers, violations, scorecard
        recording.webm   the recorded audio+video of the session

Sessions are also the candidate's application history: everything a candidate has
applied for is derived by scanning these files for their email.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR

_LOCK = threading.Lock()

# Statuses that mean "this attempt is over".
FINISHED = {"submitted", "terminated"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def session_dir(session_id: str) -> Path:
    safe = "".join(ch for ch in session_id if ch.isalnum())
    if not safe:
        raise ValueError("invalid session id")
    path = DATA_DIR / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_file(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"


def recording_path(session_id: str) -> Path:
    return session_dir(session_id) / "recording.webm"


def save(session: dict[str, Any]) -> None:
    path = session_file(session["id"])
    tmp = path.with_suffix(".tmp")
    with _LOCK:
        tmp.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def load(session_id: str) -> dict[str, Any] | None:
    path = session_file(session_id)
    if not path.exists():
        return None
    with _LOCK:
        return json.loads(path.read_text(encoding="utf-8"))


def append_recording_chunk(session_id: str, blob: bytes) -> int:
    """Chunks arrive every few seconds so a crash never loses the whole recording."""
    path = recording_path(session_id)
    with _LOCK:
        with path.open("ab") as handle:
            handle.write(blob)
        return path.stat().st_size


def _iter_sessions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for folder in DATA_DIR.iterdir():
        candidate_file = folder / "session.json"
        if not candidate_file.is_file():
            continue
        try:
            rows.append(json.loads(candidate_file.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def _summary(session: dict[str, Any]) -> dict[str, Any]:
    scorecard = session.get("scorecard") or {}
    return {
        "session_id": session.get("id"),
        "email": session.get("email"),
        "full_name": session.get("full_name") or "",
        "job_id": session.get("job_id"),
        "job_title": session.get("job_title"),
        "status": session.get("status"),
        "started_at": session.get("started_at"),
        "submitted_at": session.get("submitted_at"),
        "total_score": scorecard.get("total_score"),
        "grade": scorecard.get("grade"),
        "recommendation": scorecard.get("recommendation"),
        "violations": len(session.get("violations", [])),
        "flagged": bool(session.get("flagged")),
    }


def attempts_for_email(email: str) -> list[dict[str, Any]]:
    """Every application this candidate has made, newest first."""
    rows = [_summary(s) for s in _iter_sessions() if s.get("email") == email.lower()]
    return sorted(rows, key=lambda r: r["started_at"] or "", reverse=True)


def finished_job_ids(email: str) -> set[str]:
    """Posts this candidate has already completed (or been terminated on)."""
    return {
        row["job_id"]
        for row in attempts_for_email(email)
        if row["status"] in FINISHED and row["job_id"]
    }


def open_session_for(email: str, job_id: str) -> dict[str, Any] | None:
    """An attempt for this post that was started but never finished."""
    for session in _iter_sessions():
        if (
            session.get("email") == email.lower()
            and session.get("job_id") == job_id
            and session.get("status") not in FINISHED
        ):
            return session
    return None


def list_sessions() -> list[dict[str, Any]]:
    """Recruiter view - every attempt by everyone, newest first."""
    rows = [_summary(s) for s in _iter_sessions()]
    return sorted(rows, key=lambda r: r["started_at"] or "", reverse=True)
