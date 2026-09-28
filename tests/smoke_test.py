"""End-to-end smoke test of the whole interview flow.

    python tests/smoke_test.py

Runs against the app in-process (no server needed) and uses the heuristic scorer when
ANTHROPIC_API_KEY is unset, so it costs nothing to run.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import DATA_DIR  # noqa: E402
from app.jobs import EASY_PER_SECTION, build_question_set  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)
CANDIDATE = "smoke.candidate@example.com"
CHEATER = "smoke.cheater@example.com"


def wipe_test_sessions() -> int:
    """Sessions are the history, so a leftover run would lock the posts and fail the
    retake assertions. Remove only the folders belonging to the two test emails."""
    removed = 0
    if not DATA_DIR.exists():
        return 0
    for folder in DATA_DIR.iterdir():
        record = folder / "session.json"
        if not record.is_file():
            continue
        try:
            email = json.loads(record.read_text(encoding="utf-8")).get("email")
        except (OSError, json.JSONDecodeError):
            continue
        if email in {CANDIDATE, CHEATER}:
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
    return removed


print(f"cleaned up {wipe_test_sessions()} session(s) from a previous run")

SOLUTION = (
    "def second_largest(nums):\n"
    "    s = sorted(set(nums))\n"
    "    return s[-2] if len(s) > 1 else None\n\n"
    "print(second_largest([4, 1, 9, 9, 7]))\n"
)


def step(label: str) -> None:
    print(f"\n--- {label} ---")


# ----------------------------------------------------------------- config + login
step("config and login")
cfg = c.get("/api/config").json()
print("config:", cfg)

assert c.post("/api/auth/login", json={"email": "not-an-email"}).status_code == 400
print("invalid email rejected")

dash = c.post("/api/auth/login", json={"email": CANDIDATE}).json()
assert len(dash["posts"]) == 3
assert all(p["can_apply"] for p in dash["posts"])
print("posts:", [p["id"] for p in dash["posts"]])
print("history on first login:", dash["attempts"])

# --------------------------------------------------------------- question papers
step("every post builds a valid 100-mark paper")
for post in dash["posts"]:
    s = c.post("/api/session/start", json={"email": CANDIDATE, "job_id": post["id"]}).json()
    sid = s["session_id"]
    c.post(f"/api/session/{sid}/device-check", json={"camera": True, "microphone": True})
    c.post(f"/api/session/{sid}/confirm-jd")
    qs = c.post(f"/api/session/{sid}/begin").json()["questions"]
    assert [q["type"] for q in qs] == ["intro"] + ["theory"] * 3 + ["coding"] * 3
    assert sum(q["weight"] for q in qs) == 100
    assert len({q["id"] for q in qs}) == 7, "a question was drawn twice"
    print(f"{post['id']}: {[q['title'] for q in qs]}")

assert c.post("/api/session/start", json={"email": CANDIDATE, "job_id": "nope"}).status_code == 404
print("unknown post rejected")

# --------------------------------------------------------------- difficulty mix
step("every paper is weighted towards easy questions")
for post in dash["posts"]:
    for trial in range(50):
        paper = build_question_set(post["id"], seed=f"{post['id']}-{trial}")
        for kind in ("theory", "coding"):
            section = [q for q in paper if q["type"] == kind]
            easy = sum(1 for q in section if q.get("difficulty", "medium") == "easy")
            assert easy == EASY_PER_SECTION, (post["id"], kind, easy)
print(f"{EASY_PER_SECTION} easy + 1 medium in both sections, across 150 papers")

# ------------------------------------------------------------------- stage gating
step("stage gating")
s = c.post("/api/session/start",
           json={"email": CANDIDATE, "job_id": "python_dev_l1", "full_name": "Smoke Candidate"}).json()
sid = s["session_id"]
assert c.get(f"/api/session/{sid}/jd").status_code == 409, "JD must be gated behind devices"

r = c.post(f"/api/session/{sid}/device-check", json={"camera": False, "microphone": True}).json()
assert r["passed"] is False and r["missing"] == ["camera"]
print("camera-off blocks the check ->", r)

assert c.post(f"/api/session/{sid}/device-check",
              json={"camera": True, "microphone": True}).json()["passed"] is True
jd = c.get(f"/api/session/{sid}/jd").json()["job_description"]
assert "plan" not in jd, "the internal question plan must never reach the browser"
c.post(f"/api/session/{sid}/confirm-jd")
begin = c.post(f"/api/session/{sid}/begin").json()
questions = begin["questions"]
assert all("expectations" not in q for q in questions), "grading notes leaked to the browser"
assert all("difficulty" not in q for q in questions), "difficulty leaked to the browser"
assert all("difficulty" not in q for q in questions), "difficulty leaked to the browser"
print("remaining:", begin["remaining_seconds"], "s | proctor:", begin["proctor"])

# ----------------------------------------------------------------- code execution
step("code execution")
run = c.post(f"/api/session/{sid}/run-code", json={"code": SOLUTION}).json()
assert run["exit_code"] == 0 and "7" in run["stdout"], run
print("run-code ->", run["stdout"].strip())

bad = c.post(f"/api/session/{sid}/run-code", json={"code": "while True: pass"}).json()
assert bad["timed_out"] is True
print("infinite loop killed ->", bad["stderr"])

# --------------------------------------------------------------------- recording
step("recording")
c.post(f"/api/session/{sid}/recording-chunk", content=b"\x1aE\xdf\xa3fake-webm-header")
c.post(f"/api/session/{sid}/recording-chunk", content=b"more-bytes")
rec = c.get(f"/api/session/{sid}/recording")
assert rec.status_code == 200 and rec.content.startswith(b"\x1aE\xdf\xa3")
print("recording bytes:", len(rec.content))

# ----------------------------------------------------------------------- answers
step("answers")
for i, q in enumerate(questions):
    c.post(
        f"/api/session/{sid}/answer",
        json={
            "question_id": q["id"],
            "answer": "" if i == 6 else "A reasonably detailed written answer. " * 6,
            "code": SOLUTION if q["type"] == "coding" and i != 6 else "",
            "code_output": run["stdout"] if q["type"] == "coding" and i != 6 else "",
            "explanation": "" if i == 6 else "I talked through the approach and complexity. " * 5,
            "seconds_spent": 90,
        },
    )
assert c.post(f"/api/session/{sid}/answer", json={"question_id": "nope"}).status_code == 400
print("unknown question id rejected")

# -------------------------------------------------------------------- scorecard
step("scorecard")
card = c.post(f"/api/session/{sid}/submit",
              json={"reason": "submitted", "elapsed_seconds": 700}).json()["scorecard"]
print("engine:", card["engine"], "| error:", card["engine_error"])
print("total:", card["total_score"], "/ 100 |", card["grade"], "|", card["recommendation"])
print("sections:", card["section_scores"])
assert 0 <= card["total_score"] <= 100
assert len(card["breakdown"]) == 7
assert card["integrity"]["violation_count"] == 0
assert card["breakdown"][6]["earned"] < card["breakdown"][5]["earned"], "blank answer scored too high"
# the candidate's name is captured at start and must survive onto the card and the history
assert card["candidate"] == "Smoke Candidate", card["candidate"]
assert c.get(f"/api/session/{sid}/scorecard").json()["scorecard"]["candidate"] == "Smoke Candidate"
assert any(a["full_name"] == "Smoke Candidate"
           for a in c.get("/api/sessions").json()["sessions"]), "name missing from recruiter view"
print("candidate name carried onto the scorecard and the recruiter list")

again = c.post(f"/api/session/{sid}/submit", json={}).json()
assert again["scorecard"]["total_score"] == card["total_score"], "re-submit must be idempotent"
print("re-submit is idempotent")

# -------------------------------------------------------------------- proctoring
step("proctoring escalation")
s = c.post("/api/session/start", json={"email": CHEATER, "job_id": "python_dev_l1"}).json()
psid = s["session_id"]
c.post(f"/api/session/{psid}/device-check", json={"camera": True, "microphone": True})
c.post(f"/api/session/{psid}/confirm-jd")
c.post(f"/api/session/{psid}/begin")

assert c.post(f"/api/session/{psid}/violation", json={"type": "made_up"}).status_code == 400
print("unknown violation type rejected")

for i in range(1, cfg["proctor_terminate_at"] + 1):
    v = c.post(f"/api/session/{psid}/violation",
               json={"type": "tab_hidden", "detail": f"switch {i}", "at_second": i * 30}).json()
    print(f"  flag {i}: alarm={v['alarm']} terminate={v['terminate']} left={v['remaining_before_termination']}")
    assert v["alarm"] == (i >= cfg["proctor_alarm_at"])
    assert v["terminate"] == (i >= cfg["proctor_terminate_at"])

out = c.post(f"/api/session/{psid}/submit", json={"reason": "proctoring_terminated"}).json()
assert out["status"] == "terminated"
integrity = out["scorecard"]["integrity"]
print("integrity:", {k: v for k, v in integrity.items() if k != "events"})
assert integrity["terminated"] and integrity["flagged"]
assert integrity["violation_count"] == cfg["proctor_terminate_at"]
# an empty attempt must not come back as "Borderline"
assert out["scorecard"]["total_score"] == 0
assert out["scorecard"]["recommendation"] == "No Hire", out["scorecard"]["recommendation"]
print("recommendation tracks the score:", out["scorecard"]["recommendation"])
assert c.post(f"/api/session/{psid}/violation", json={"type": "tab_hidden"}).status_code == 409
print("violations rejected after termination")

# ------------------------------------------------------- dashboard + retake rule
step("dashboard history and retake rule")
dash = c.post("/api/auth/login", json={"email": CHEATER}).json()
row = dash["attempts"][0]
print("history row:", row)
assert row["status"] == "terminated" and row["flagged"] and row["violations"] == cfg["proctor_terminate_at"]

python_post = next(p for p in dash["posts"] if p["id"] == "python_dev_l1")
assert python_post["already_attempted"] and not python_post["can_apply"]
assert next(p for p in dash["posts"] if p["id"] == "data_engineer_l1")["can_apply"]
print("completed post locked, other posts still open")

retake = c.post("/api/session/start", json={"email": CHEATER, "job_id": "python_dev_l1"})
assert retake.status_code == 409
print("retake ->", retake.json()["detail"])

past = c.get(f"/api/session/{psid}/scorecard").json()
assert past["scorecard"]["total_score"] == out["scorecard"]["total_score"]
assert past["status"] == "terminated"
print("past scorecard can be re-opened from the dashboard")

# an abandoned attempt does not lock the post
s2 = c.post("/api/session/start", json={"email": CHEATER, "job_id": "data_engineer_l1"}).json()
s3 = c.post("/api/session/start", json={"email": CHEATER, "job_id": "data_engineer_l1"}).json()
assert s2["session_id"] != s3["session_id"]
statuses = {a["session_id"]: a["status"] for a in c.post("/api/auth/login", json={"email": CHEATER}).json()["attempts"]}
assert statuses[s2["session_id"]] == "abandoned", statuses
print("restarting an unfinished attempt closes the old one:", statuses[s2["session_id"]])

print("\nALL CHECKS PASSED")
