# L1 Interview Agent — automated Python screening

A candidate logs in with their email, sees their application history and the open posts,
picks one, passes a camera + microphone check, reads and confirms the job description, then
answers **1 introduction + 3 theory + 3 coding questions in 30 minutes** — fullscreen,
recorded and proctored — while explaining every answer out loud. Claude grades the session
and produces a **scorecard out of 100**.

## Quick start

```powershell
python -m pip install -r requirements.txt
copy .env.example .env          # then put your ANTHROPIC_API_KEY in it
python run.py
```

Open **http://localhost:8000** in **Chrome or Edge**. Camera, microphone, fullscreen and
live speech transcription need a Chromium browser on `localhost` or an `https://` origin.

Run the tests (no API key needed, costs nothing):

```powershell
python tests\smoke_test.py    # full flow: papers, gating, code run, proctoring, scoring
python tests\dom_check.py     # every id app.js touches exists in index.html
```

## The flow

| Stage | What happens |
|---|---|
| 1. Login | Email is validated. Optionally restrict domains with `ALLOWED_EMAIL_DOMAINS`. |
| 2. Dashboard | **Your applications**: every interview taken, when, its status, score /100, outcome, proctoring flags, and a link to reopen the scorecard. **Open positions**: the posts you can still apply for. A post you have completed is locked (`ALLOW_RETAKE=true` reopens it). |
| 3. Device check | `getUserMedia` for camera + mic, live preview and a mic level meter. **Both must be live** — Continue only appears after the server confirms the check passed. |
| 4. Job description | The JD for the post you picked, plus the interview rules, behind a confirmation checkbox. |
| 5. Interview | Fullscreen, 30-minute countdown, camera pinned top-right and recording, one question at a time, a Python editor with **Run code** for coding questions, and **Start explaining** to transcribe your spoken answer. Auto-submits at 00:00. |
| 6. Scorecard | Score /100, grade, recommendation, integrity panel, strengths, improvements, per-question breakdown, recording download — then **Back to dashboard** or **Exit and log out**. |

## Job posts

Three posts ship in [app/jobs.py](app/jobs.py): **Python Developer L1**, **Data Engineer L1
(Python + SQL)** and **Automation QA Engineer L1 (Python)**. A post declares a *question
plan* — how many theory and coding questions to draw from which bank — so the Data Engineer
paper leans SQL while still testing core Python:

```python
"plan": {"theory": [("sql_data", 2), ("python_core", 1)],
         "coding": [("sql_data", 2), ("python_core", 1)]}
```

Banks live in [app/questions.py](app/questions.py) (`python_core`, `sql_data`, `automation`;
41 questions in total). Each session draws its paper seeded by the session id, so two
candidates rarely get the same questions. The `expectations` on each question are grading
notes — sent to Claude, **never** to the browser (the smoke test asserts this).

### Difficulty

This is an L1 screen for freshers, so every question is tagged `"difficulty": "easy"` or
`"medium"` (missing means medium), and **each paper is 2 easy + 1 medium in both the theory
and the coding section** — set by `EASY_PER_SECTION` in [app/jobs.py](app/jobs.py). The plan
decides *which bank* a question comes from; the quota decides *how hard* it is. Easy means
FizzBuzz, counting vowels, filtering a list of dicts; medium means group-anagrams or a
running total per group. Difficulty is a sampling hint only: it never reaches the browser
and it does not change the marks, which stay 15 per question.

If a bank runs short of one difficulty the remainder is topped up from the other, so adding
questions can never make paper generation fail.

To add a post, append to `JOBS`. To add questions, append to a bank — and tag the easy ones,
or they default to medium.

## Proctoring — what it really does

**A web page cannot stop you opening another window.** No browser allows that. What this
app does instead is make leaving expensive and visible:

- The interview runs **fullscreen**; leaving it raises a blocking "Interview paused" overlay
  (the clock keeps running).
- Every switch away is recorded: tab hidden, window blur, fullscreen exit, right-click,
  copy/cut/paste (blocked), devtools and new-window shortcuts (blocked where the browser
  allows it), camera or mic stopping mid-interview, and a second display being connected.
- Repeat events of the same kind inside 2 seconds count once, so one Alt-Tab is one flag,
  not three.
- **The server owns the escalation**, not the browser: it counts the flags and decides.
  At `PROCTOR_ALARM_AT` (default 3) the candidate gets a full-screen red alarm with a beep;
  at `PROCTOR_TERMINATE_AT` (default 6) the interview ends immediately, is scored on
  whatever exists, and the attempt is marked **terminated** and flagged on the dashboard.
- Unknown event types are rejected, so a tampered client cannot invent flags.

Flags are shown to the reviewer and given to Claude as context, but they **do not silently
reduce the marks** — the work is scored on its merits and the pattern is called out in the
summary. That split is deliberate: a human decides what a flag is worth.

What it does **not** do: detect a phone, a second person in the room, a screen reader on
another machine, or a candidate reading from a printout. For that you need webcam-based
face/gaze analysis on the recording, which this does not have.

## Scoring

[app/scoring.py](app/scoring.py) sends Claude (`claude-opus-5`, adaptive thinking,
structured output) the JD, every question with its internal expectations, the written
answer, the code, the output of running that code, the speech-to-text transcript and the
proctoring log. Claude returns three 0–10 axes per question:

| Axis | Weight inside a question |
|---|---|
| correctness | 50% |
| explanation (does the spoken answer show real understanding) | 30% |
| communication | 20% |

**Python — not the model — computes the total**, from those axes and the per-question
weights (intro 10 + theory 3×15 + coding 3×15 = 100), so the total is always arithmetically
consistent.

Without `ANTHROPIC_API_KEY` the app still runs end to end but falls back to a crude
length-based heuristic, clearly labelled as such on the scorecard.

## Recording

`MediaRecorder` flushes a chunk every 5 seconds to `POST /api/session/{id}/recording-chunk`,
appended to `data/sessions/<id>/recording.webm`. A crash or closed tab loses at most
5 seconds. Download it from the scorecard or `GET /api/session/{id}/recording`.

## Data layout

```
data/sessions/<session_id>/
    session.json     candidate, post, questions, answers, transcripts, violations, scorecard
    recording.webm   audio + video of the session
data/tmp/            scratch space for candidate code runs
```

There is no database — a candidate's history is derived by scanning these files for their
email. Fine for one machine and a few hundred interviews; move to SQLite or Postgres beyond
that.

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for real scoring. |
| `ALLOWED_EMAIL_DOMAINS` | empty (any) | e.g. `alignedautomation.com,gmail.com` |
| `INTERVIEW_MINUTES` | `30` | Total interview time. |
| `SCORING_MODEL` | `claude-opus-5` | Model used for grading. |
| `PROCTOR_ALARM_AT` | `3` | Flags before the on-screen alarm. |
| `PROCTOR_TERMINATE_AT` | `6` | Flags before the interview is ended automatically. |
| `ALLOW_RETAKE` | `false` | Allow a second attempt at a post already completed. |
| `CODE_RUN_TIMEOUT_SECONDS` | `8` | Kill limit for candidate code. |
| `RUN_TMP_DIR` | `data/tmp` | Where candidate code runs (kept off the system drive). |

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Email login; returns history + open posts. |
| GET | `/api/dashboard?email=` | Same payload, for refreshing. |
| POST | `/api/session/start` | Start an attempt for a post. |
| POST | `/api/session/{id}/device-check` | Records the camera/mic result; gates the next stage. |
| GET | `/api/session/{id}/jd` | Job description for this attempt. |
| POST | `/api/session/{id}/confirm-jd` | Candidate confirmation. |
| POST | `/api/session/{id}/begin` | Starts the clock, returns the questions. |
| POST | `/api/session/{id}/answer` | Autosave one answer + code + explanation. |
| POST | `/api/session/{id}/violation` | Report suspicious activity; server decides alarm/terminate. |
| POST | `/api/session/{id}/run-code` | Runs the snippet in a subprocess with a timeout. |
| POST | `/api/session/{id}/recording-chunk` | Appends a recording chunk. |
| POST | `/api/session/{id}/submit` | Ends the interview and generates the scorecard (idempotent). |
| GET | `/api/session/{id}/scorecard` | Fetch an existing scorecard. |
| GET | `/api/session/{id}/recording` | Download the .webm. |
| GET | `/api/sessions` | Recruiter view: every attempt by everyone. |

## Deployment

The app needs **one long-lived process with a persistent disk**. Sessions, answers and
video recordings are files under `DATA_DIR`, and a single interview spans dozens of
requests over 30 minutes.

### Vercel — works, but sessions do not survive

[`vercel.json`](vercel.json) deploys the app to Vercel. Vercel auto-detects the FastAPI
app in [`app/main.py`](app/main.py) and serves every route through it, so no extra
entrypoint or rewrite rule is needed — adding a `rewrites` rule actually *breaks* routing,
because the app then receives the rewritten path instead of the real one and 404s on
everything.

`vercel.json` only sets `DATA_DIR` and `RUN_TMP_DIR` to paths under `/tmp`, the one writable
location in a serverless bundle. Without them `app/config.py` tries to create its data
directories inside the read-only deployment and the app dies at import.

**Use this for demos, not for real interviews.** `/tmp` belongs to one function instance and
is wiped when that instance is recycled. A single candidate on an idle project will usually
stay on one warm instance and get through fine, but nothing guarantees it: a cold start or a
second concurrent candidate produces `404 session not found` part-way through an interview,
and any recording collected so far is gone. Scorecards are lost the same way.

To make Vercel genuinely safe you would move the session store off the filesystem — Vercel
Postgres or KV for sessions, Blob for recordings — which means rewriting `app/storage.py`.
Until then, prefer the Render blueprint below for anything that matters.

### Render — the durable option

[`render.yaml`](render.yaml) is a ready blueprint for [Render](https://render.com):

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → pick the repo. It reads `render.yaml`.
3. Set `ANTHROPIC_API_KEY` (and ideally `ALLOWED_EMAIL_DOMAINS`) in the dashboard —
   they are marked `sync: false` so they never live in git.
4. Deploy. Health check is `GET /api/config`.

The blueprint mounts a 5 GB disk at `/var/data` and points `DATA_DIR` and `RUN_TMP_DIR` at
it. A disk requires a paid instance type; on the free tier the service also sleeps when
idle, which will drop an interview in progress.

Railway, Fly.io, Azure App Service or any Docker host work the same way — set `HOST=0.0.0.0`,
point `DATA_DIR` at a mounted volume, and provide `ANTHROPIC_API_KEY`.

**Read "Known limits" below before putting this on a public URL.** Three things there are
deployment blockers, not nice-to-haves: there is no real authentication, `GET /api/sessions`
exposes every candidate's scorecard to anyone, and `/run-code` executes candidate-supplied
Python on your server.

## Known limits (deliberate, for this version)

- **No authentication beyond the email.** Anyone with the URL can claim any email address
  and see that candidate's history. Add a magic link or SSO before external use — this is
  the most important gap.
- **`/run-code` is not a hardened sandbox.** It runs candidate code as a real subprocess
  with `-I`, an empty `PATH`, a scrubbed environment and an 8-second timeout. The scrubbing
  matters: without it a candidate could `print(os.environ)` and read `ANTHROPIC_API_KEY`
  straight off the server. What remains is still a real process on your host — it can use
  CPU and memory, and reach the network. Move it into Docker/nsjail before exposing this
  to candidates you do not trust.
- **Speech transcription is browser-side** (Web Speech API, Chrome/Edge only) and the
  candidate can edit the text before it is scored. The audio is in the recording either way;
  swap in server-side transcription for a tamper-proof version.
- **Proctoring is detection, not prevention** — see the section above for exactly what it
  can and cannot see.
- **`GET /api/sessions` is unprotected.** It exposes every candidate's score. Put it behind
  auth or delete it before this leaves your machine.
