"""L1 Interview Agent - FastAPI backend."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import scoring, storage
from .config import (
    ALLOW_RETAKE,
    ALLOWED_EMAIL_DOMAINS,
    CODE_RUN_TIMEOUT_SECONDS,
    INTERVIEW_SECONDS,
    PROCTOR_ALARM_AT,
    PROCTOR_TERMINATE_AT,
    RUN_TMP_DIR,
    STATIC_DIR,
)
from .jobs import build_question_set, get_job, job_description, open_posts, public_question

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")

# Events the browser may report. Anything else is rejected, so a stray client
# cannot invent event types that inflate a candidate's violation count.
VIOLATION_TYPES = {
    "tab_hidden": "Switched away from the interview tab",
    "window_blur": "Interview window lost focus",
    "fullscreen_exit": "Left fullscreen mode",
    "copy_attempt": "Tried to copy from the question",
    "paste_attempt": "Tried to paste into the answer",
    "context_menu": "Opened the right-click menu",
    "devtools_key": "Pressed a developer-tools shortcut",
    "camera_stopped": "Camera stopped during the interview",
    "microphone_stopped": "Microphone stopped during the interview",
    "multiple_displays": "More than one display is connected",
    "window_resized": "Interview window was resized substantially",
}

app = FastAPI(title="L1 Interview Agent", version="2.0.0")


# --------------------------------------------------------------------------- models


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(default="", max_length=120)


class StartRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    job_id: str
    full_name: str = Field(default="", max_length=120)


class DeviceCheckRequest(BaseModel):
    camera: bool
    microphone: bool
    camera_label: str = ""
    microphone_label: str = ""


class AnswerRequest(BaseModel):
    question_id: str
    answer: str = ""
    code: str = ""
    code_output: str = ""
    explanation: str = ""
    seconds_spent: int = 0


class RunCodeRequest(BaseModel):
    code: str = Field(max_length=20000)


class ViolationRequest(BaseModel):
    type: str
    detail: str = Field(default="", max_length=400)
    at_second: int = 0


class SubmitRequest(BaseModel):
    reason: str = "submitted"
    elapsed_seconds: int = 0


# --------------------------------------------------------------------------- helpers


def normalise_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if ALLOWED_EMAIL_DOMAINS and email.split("@")[1] not in ALLOWED_EMAIL_DOMAINS:
        allowed = ", ".join("@" + d for d in ALLOWED_EMAIL_DOMAINS)
        raise HTTPException(status_code=403, detail=f"Only {allowed} addresses may log in.")
    return email


def get_session(session_id: str) -> dict[str, Any]:
    session = storage.load(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def require_stage(session: dict[str, Any], *allowed: str) -> None:
    if session["status"] not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Session is '{session['status']}', expected one of {list(allowed)}",
        )


def remaining_seconds(session: dict[str, Any]) -> int:
    if not session.get("interview_started_at_epoch"):
        return session["duration_seconds"]
    used = time.time() - session["interview_started_at_epoch"]
    return max(0, int(session["duration_seconds"] - used))


def dashboard_payload(email: str) -> dict[str, Any]:
    attempts = storage.attempts_for_email(email)
    done = storage.finished_job_ids(email)
    posts = []
    for post in open_posts():
        attempt = next((a for a in attempts if a["job_id"] == post["id"]), None)
        posts.append(
            post
            | {
                "already_attempted": post["id"] in done,
                "can_apply": ALLOW_RETAKE or post["id"] not in done,
                "last_attempt": attempt,
            }
        )
    return {
        "email": email,
        "attempts": attempts,
        "posts": posts,
        "allow_retake": ALLOW_RETAKE,
    }


# --------------------------------------------------------------------------- routes


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    return {
        "duration_seconds": INTERVIEW_SECONDS,
        "allowed_email_domains": ALLOWED_EMAIL_DOMAINS,
        "scoring_available": bool(scoring.ANTHROPIC_API_KEY),
        "proctor_alarm_at": PROCTOR_ALARM_AT,
        "proctor_terminate_at": PROCTOR_TERMINATE_AT,
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    """No password - the email identifies the candidate. See README's limitations."""
    email = normalise_email(payload.email)
    return dashboard_payload(email)


@app.get("/api/dashboard")
def dashboard(email: str) -> dict[str, Any]:
    return dashboard_payload(normalise_email(email))


@app.post("/api/session/start")
def start_session(payload: StartRequest) -> dict[str, Any]:
    email = normalise_email(payload.email)
    job = get_job(payload.job_id)
    if job is None or not job["active"]:
        raise HTTPException(status_code=404, detail="That post is no longer open.")

    if not ALLOW_RETAKE and payload.job_id in storage.finished_job_ids(email):
        raise HTTPException(
            status_code=409,
            detail="You have already completed the interview for this post.",
        )

    # An abandoned attempt for the same post is closed out rather than left dangling.
    stale = storage.open_session_for(email, payload.job_id)
    if stale is not None:
        stale["status"] = "abandoned"
        stale["events"].append({"at": storage.now_iso(), "event": "abandoned"})
        storage.save(stale)

    session_id = storage.new_session_id()
    questions = build_question_set(payload.job_id, seed=session_id)
    session = {
        "id": session_id,
        "email": email,
        "full_name": payload.full_name.strip(),
        "job_id": job["id"],
        "job_title": job["title"],
        "status": "logged_in",
        "started_at": storage.now_iso(),
        "duration_seconds": INTERVIEW_SECONDS,
        "job_description": job_description(job),
        "questions": questions,
        "answers": {},
        "violations": [],
        "flagged": False,
        "events": [{"at": storage.now_iso(), "event": "session_created", "job": job["id"]}],
        "device_check": None,
        "jd_confirmed_at": None,
        "interview_started_at": None,
        "interview_started_at_epoch": None,
        "submitted_at": None,
        "elapsed_seconds": 0,
        "scorecard": None,
        "recording_bytes": 0,
    }
    storage.save(session)
    return {
        "session_id": session_id,
        "email": email,
        "job_id": job["id"],
        "job_title": job["title"],
        "status": session["status"],
        "duration_seconds": INTERVIEW_SECONDS,
        "question_count": len(questions),
    }


@app.post("/api/session/{session_id}/device-check")
def device_check(session_id: str, payload: DeviceCheckRequest) -> dict[str, Any]:
    session = get_session(session_id)
    require_stage(session, "logged_in", "devices_ok")

    ok = payload.camera and payload.microphone
    session["device_check"] = {
        "camera": payload.camera,
        "microphone": payload.microphone,
        "camera_label": payload.camera_label,
        "microphone_label": payload.microphone_label,
        "checked_at": storage.now_iso(),
        "passed": ok,
    }
    session["events"].append(
        {"at": storage.now_iso(), "event": "device_check", "passed": ok}
    )
    if ok:
        session["status"] = "devices_ok"
    storage.save(session)

    if not ok:
        missing = [
            name
            for name, present in (
                ("camera", payload.camera),
                ("microphone", payload.microphone),
            )
            if not present
        ]
        return {"passed": False, "missing": missing}
    return {"passed": True, "status": session["status"]}


@app.get("/api/session/{session_id}/jd")
def get_jd(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    require_stage(session, "devices_ok", "jd_confirmed", "in_progress")
    return {"job_description": session["job_description"]}


@app.post("/api/session/{session_id}/confirm-jd")
def confirm_jd(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    require_stage(session, "devices_ok")
    session["status"] = "jd_confirmed"
    session["jd_confirmed_at"] = storage.now_iso()
    session["events"].append({"at": storage.now_iso(), "event": "jd_confirmed"})
    storage.save(session)
    return {"status": session["status"]}


@app.post("/api/session/{session_id}/begin")
def begin_interview(session_id: str) -> dict[str, Any]:
    """Starts the clock and hands over the questions."""
    session = get_session(session_id)
    require_stage(session, "jd_confirmed", "in_progress")

    if session["status"] == "jd_confirmed":
        session["status"] = "in_progress"
        session["interview_started_at"] = storage.now_iso()
        session["interview_started_at_epoch"] = time.time()
        session["events"].append({"at": storage.now_iso(), "event": "interview_started"})
        storage.save(session)

    return {
        "status": session["status"],
        "job_title": session["job_title"],
        "questions": [public_question(q) for q in session["questions"]],
        "remaining_seconds": remaining_seconds(session),
        "answers": session["answers"],
        "proctor": {
            "alarm_at": PROCTOR_ALARM_AT,
            "terminate_at": PROCTOR_TERMINATE_AT,
            "violations": len(session["violations"]),
        },
    }


@app.post("/api/session/{session_id}/answer")
def save_answer(session_id: str, payload: AnswerRequest) -> dict[str, Any]:
    session = get_session(session_id)
    require_stage(session, "in_progress")

    if not any(q["id"] == payload.question_id for q in session["questions"]):
        raise HTTPException(status_code=400, detail="Unknown question id")

    previous = session["answers"].get(payload.question_id, {})
    session["answers"][payload.question_id] = {
        "answer": payload.answer,
        "code": payload.code,
        "code_output": payload.code_output or previous.get("code_output", ""),
        "explanation": payload.explanation,
        "seconds_spent": max(payload.seconds_spent, previous.get("seconds_spent", 0)),
        "updated_at": storage.now_iso(),
    }
    storage.save(session)
    return {"saved": True, "remaining_seconds": remaining_seconds(session)}


@app.post("/api/session/{session_id}/violation")
def report_violation(session_id: str, payload: ViolationRequest) -> dict[str, Any]:
    """The browser reports suspicious activity; the server owns the escalation."""
    session = get_session(session_id)
    require_stage(session, "in_progress")

    if payload.type not in VIOLATION_TYPES:
        raise HTTPException(status_code=400, detail="Unknown violation type")

    session["violations"].append(
        {
            "type": payload.type,
            "label": VIOLATION_TYPES[payload.type],
            "detail": payload.detail,
            "at_second": payload.at_second,
            "at": storage.now_iso(),
        }
    )
    count = len(session["violations"])
    terminate = count >= PROCTOR_TERMINATE_AT
    if count >= PROCTOR_ALARM_AT:
        session["flagged"] = True
    storage.save(session)

    return {
        "count": count,
        "label": VIOLATION_TYPES[payload.type],
        "alarm": count >= PROCTOR_ALARM_AT,
        "terminate": terminate,
        "remaining_before_termination": max(0, PROCTOR_TERMINATE_AT - count),
    }


# Candidate code must not inherit our process environment - ANTHROPIC_API_KEY
# lives there. Keep only the handful of variables CPython needs to start, so a
# snippet like `print(os.environ)` returns nothing of ours.
_ENV_KEYS_CANDIDATE_CODE_MAY_SEE = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "NUMBER_OF_PROCESSORS",
)


def sandbox_env() -> dict[str, str]:
    """A scrubbed environment for the candidate's subprocess."""
    env = {k: os.environ[k] for k in _ENV_KEYS_CANDIDATE_CODE_MAY_SEE if k in os.environ}
    # Empty PATH so the snippet cannot shell out to tools it happens to find.
    env["PATH"] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


@app.post("/api/session/{session_id}/run-code")
def run_code(session_id: str, payload: RunCodeRequest) -> dict[str, Any]:
    """Runs the candidate's snippet in a short-lived subprocess so they can self-check."""
    session = get_session(session_id)
    require_stage(session, "in_progress")

    with tempfile.TemporaryDirectory(dir=RUN_TMP_DIR) as workdir:
        script = Path(workdir) / "candidate.py"
        script.write_text(payload.code, encoding="utf-8")
        try:
            completed = subprocess.run(  # noqa: S603 - scrubbed env, no PATH, hard timeout
                [sys.executable, "-I", "-B", str(script)],
                capture_output=True,
                text=True,
                timeout=CODE_RUN_TIMEOUT_SECONDS,
                cwd=workdir,
                env=sandbox_env(),
            )
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {CODE_RUN_TIMEOUT_SECONDS}s.",
                "exit_code": -1,
                "timed_out": True,
            }

    return {
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
        "exit_code": completed.returncode,
        "timed_out": False,
    }


@app.post("/api/session/{session_id}/recording-chunk")
async def recording_chunk(session_id: str, request: Request) -> dict[str, Any]:
    session = get_session(session_id)
    blob = await request.body()
    if not blob:
        return {"bytes": session.get("recording_bytes", 0)}
    total = storage.append_recording_chunk(session_id, blob)
    session["recording_bytes"] = total
    storage.save(session)
    return {"bytes": total}


@app.get("/api/session/{session_id}/recording")
def get_recording(session_id: str) -> FileResponse:
    get_session(session_id)
    path = storage.recording_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No recording for this session")
    return FileResponse(path, media_type="video/webm", filename=f"{session_id}.webm")


@app.post("/api/session/{session_id}/submit")
def submit(session_id: str, payload: SubmitRequest) -> dict[str, Any]:
    session = get_session(session_id)
    if session["status"] in storage.FINISHED and session.get("scorecard"):
        return {"status": session["status"], "scorecard": session["scorecard"]}
    require_stage(session, "in_progress", *storage.FINISHED)

    terminated = payload.reason == "proctoring_terminated"
    session["status"] = "scoring"
    session["submitted_at"] = storage.now_iso()
    session["submit_reason"] = payload.reason
    session["elapsed_seconds"] = payload.elapsed_seconds or (
        session["duration_seconds"] - remaining_seconds(session)
    )
    session["events"].append(
        {"at": storage.now_iso(), "event": "submitted", "reason": payload.reason}
    )
    storage.save(session)

    scorecard = scoring.build_scorecard(session)
    session["scorecard"] = scorecard
    session["status"] = "terminated" if terminated else "submitted"
    storage.save(session)
    return {"status": session["status"], "scorecard": scorecard}


@app.get("/api/session/{session_id}/scorecard")
def get_scorecard(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session.get("scorecard"):
        raise HTTPException(status_code=404, detail="Scorecard not generated yet")
    return {
        "email": session["email"],
        "session_id": session["id"],
        "job_title": session["job_title"],
        "status": session["status"],
        "submitted_at": session["submitted_at"],
        "scorecard": session["scorecard"],
        "questions": [public_question(q) for q in session["questions"]],
        "answers": session["answers"],
        "violations": session.get("violations", []),
    }


@app.get("/api/sessions")
def all_sessions() -> dict[str, Any]:
    """Recruiter view of every attempt."""
    return {"sessions": storage.list_sessions()}


# --------------------------------------------------------------------------- static


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
