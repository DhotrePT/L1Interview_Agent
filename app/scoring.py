"""Scorecard generation.

Claude grades every answer on three axes (0-10 each). The final score out of 100 is
computed in Python from those axes and the per-question weights, so the total is always
arithmetically consistent and never hallucinated.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .config import ANTHROPIC_API_KEY, SCORING_MODEL

# Axis weights inside a single question.
AXIS_WEIGHTS = {"correctness": 0.50, "explanation": 0.30, "communication": 0.20}

SYSTEM_PROMPT = """You are a senior Python engineer grading a recorded L1 (entry level, \
0-2 years) screening interview. You receive the job description, and for every question: \
the question, the internal expectations, the candidate's written answer, any code they \
wrote, the output of running that code, and the transcript of them explaining the answer \
out loud.

Grade each question on three axes, 0-10 integers:
- correctness  : Is the answer/code technically right and complete for an L1 candidate? \
For the introduction question, score relevance and substance of their background instead.
- explanation  : Does their spoken explanation show they actually understand what they \
wrote? Reasoning, complexity, trade-offs, edge cases. An empty or copy-pasted-sounding \
explanation scores low even if the code is perfect.
- communication: Clarity, structure and confidence of the spoken explanation.

Rules:
- Be fair but calibrated for an L1 hire. 5 = acceptable junior answer, 8+ = clearly strong, \
2 or below = essentially no usable answer.
- If a question was left blank, score every axis 0 and say so in the feedback.
- If the explanation transcript is empty, cap explanation and communication at 3 and note \
that the candidate did not explain the answer out loud.
- Never invent things the candidate did not say or write.
- Keep feedback specific and short: what was right, what was missing, one improvement.
- You are also shown a proctoring log (tab switches, leaving fullscreen, paste attempts). \
Do NOT silently lower the per-question scores because of it - score the work on its merits. \
Mention the pattern in "summary" and in "red_flags" on the affected question only when the \
log genuinely undermines confidence in the answer (for example a long tab switch \
immediately before a suspiciously polished answer).

Return JSON only, no prose, matching exactly this shape:
{
  "questions": [
    {"id": "<question id>", "correctness": 0-10, "explanation": 0-10,
     "communication": 0-10, "feedback": "2-3 sentences", "red_flags": ["..."]}
  ],
  "strengths": ["..."],
  "improvements": ["..."],
  "recommendation": "Strong Hire | Hire | Borderline | No Hire",
  "summary": "3-4 sentence overall summary addressed to the hiring manager"
}
Include exactly one entry in "questions" for every question you were given, in the same \
order."""

RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "correctness": {"type": "integer", "minimum": 0, "maximum": 10},
                    "explanation": {"type": "integer", "minimum": 0, "maximum": 10},
                    "communication": {"type": "integer", "minimum": 0, "maximum": 10},
                    "feedback": {"type": "string"},
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "id",
                    "correctness",
                    "explanation",
                    "communication",
                    "feedback",
                    "red_flags",
                ],
                "additionalProperties": False,
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "improvements": {"type": "array", "items": {"type": "string"}},
        "recommendation": {
            "type": "string",
            "enum": ["Strong Hire", "Hire", "Borderline", "No Hire"],
        },
        "summary": {"type": "string"},
    },
    "required": [
        "questions",
        "strengths",
        "improvements",
        "recommendation",
        "summary",
    ],
    "additionalProperties": False,
}


def _transcript(session: dict[str, Any]) -> str:
    """The full interview rendered as text for the grader."""
    jd = session["job_description"]
    parts = [
        "=== JOB DESCRIPTION ===",
        f"{jd['title']} ({jd['experience']})",
        jd["summary"],
        "Must have: " + "; ".join(jd["must_have"]),
        "",
        "=== CANDIDATE ===",
        f"Email: {session['email']}",
        f"Applied for: {session.get('job_title', jd['title'])}",
        f"Time used: {session.get('elapsed_seconds', 0) // 60} min "
        f"of {session['duration_seconds'] // 60} min",
        f"Interview ended by: {session.get('submit_reason', 'submitted')}",
        "",
        "=== PROCTORING LOG ===",
    ]

    violations = session.get("violations", [])
    if not violations:
        parts.append("No suspicious activity recorded.")
    else:
        for event in violations:
            parts.append(
                f"[{event['at_second']}s into the interview] {event['label']}"
                + (f" - {event['detail']}" if event.get("detail") else "")
            )
    parts.append("")

    for question in session["questions"]:
        answer = session["answers"].get(question["id"], {})
        parts.append(f"=== QUESTION {question['number']} [{question['type']}] "
                     f"(id: {question['id']}, weight {question['weight']}) ===")
        parts.append(f"Title: {question['title']}")
        parts.append(f"Asked: {question['prompt']}")
        parts.append("Internal expectations: " + " | ".join(question["expectations"]))
        parts.append(f"Time spent on this question: {answer.get('seconds_spent', 0)}s")

        written = (answer.get("answer") or "").strip()
        code = (answer.get("code") or "").strip()
        output = (answer.get("code_output") or "").strip()
        spoken = (answer.get("explanation") or "").strip()

        parts.append("--- Written answer ---")
        parts.append(written if written else "(blank)")
        if question["type"] == "coding":
            parts.append("--- Code submitted ---")
            parts.append(code if code else "(no code written)")
            parts.append("--- Output of last run ---")
            parts.append(output if output else "(candidate never ran the code)")
        parts.append("--- Spoken explanation (speech-to-text transcript) ---")
        parts.append(spoken if spoken else "(no explanation recorded)")
        parts.append("")

    return "\n".join(parts)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _grade_with_claude(session: dict[str, Any]) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY or None)
    user_content = (
        _transcript(session)
        + "\n\nGrade this interview now and return only the JSON object."
    )

    kwargs: dict[str, Any] = {
        "model": SCORING_MODEL,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "thinking": {"type": "adaptive"},
        "messages": [{"role": "user", "content": user_content}],
    }

    try:
        with client.messages.stream(
            output_config={"format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
            **kwargs,
        ) as stream:
            message = stream.get_final_message()
    except TypeError:
        # Older SDK without output_config - fall back to prompt-enforced JSON.
        with client.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a fallback reason
        if "output_config" not in str(exc):
            raise
        with client.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()

    text = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    )
    return _extract_json(text)


def _grade_heuristically(session: dict[str, Any]) -> dict[str, Any]:
    """Offline fallback: length/keyword based, clearly labelled as un-reviewed."""
    graded = []
    for question in session["questions"]:
        answer = session["answers"].get(question["id"], {})
        written = (answer.get("answer") or "").strip()
        code = (answer.get("code") or "").strip()
        spoken = (answer.get("explanation") or "").strip()
        body = written if question["type"] != "coding" else code or written

        def band(text: str, full: int) -> int:
            words = len(text.split())
            if words == 0:
                return 0
            for threshold, score in ((8, 2), (20, 4), (45, 5), (90, 6)):
                if words < threshold:
                    return min(full, score)
            return full

        correctness = band(body, 7)
        if question["type"] == "coding" and "def " in code:
            correctness = min(8, correctness + 2)
        graded.append(
            {
                "id": question["id"],
                "correctness": correctness,
                "explanation": band(spoken, 7),
                "communication": band(spoken, 6),
                "feedback": "Automatic offline estimate - no model review was available.",
                "red_flags": [],
            }
        )

    return {
        "questions": graded,
        "strengths": [],
        "improvements": ["Re-run scoring with ANTHROPIC_API_KEY set for a real review."],
        # No recommendation here - it is derived from the total in build_scorecard,
        # which is the only place the total is known.
        "summary": (
            "Heuristic scorecard only. ANTHROPIC_API_KEY was not configured, so answers "
            "were scored by length rather than by content. Treat this as a placeholder."
        ),
    }


def build_scorecard(session: dict[str, Any]) -> dict[str, Any]:
    """Grade the session and return the final scorecard (total out of 100)."""
    engine = "claude"
    error: str | None = None

    if ANTHROPIC_API_KEY:
        try:
            raw = _grade_with_claude(session)
        except Exception as exc:  # noqa: BLE001 - never lose an interview to a grading error
            engine = "heuristic"
            error = f"{type(exc).__name__}: {exc}"
            raw = _grade_heuristically(session)
    else:
        engine = "heuristic"
        error = "ANTHROPIC_API_KEY is not set"
        raw = _grade_heuristically(session)

    by_id = {row.get("id"): row for row in raw.get("questions", [])}
    breakdown: list[dict[str, Any]] = []
    total = 0.0

    for question in session["questions"]:
        row = by_id.get(question["id"], {})
        axes = {
            axis: max(0, min(10, int(row.get(axis, 0) or 0)))
            for axis in AXIS_WEIGHTS
        }
        ratio = sum(axes[axis] * weight for axis, weight in AXIS_WEIGHTS.items()) / 10
        earned = round(question["weight"] * ratio, 1)
        total += earned
        breakdown.append(
            {
                "id": question["id"],
                "number": question["number"],
                "type": question["type"],
                "title": question["title"],
                "weight": question["weight"],
                "earned": earned,
                "axes": axes,
                "feedback": row.get("feedback", "No feedback returned."),
                "red_flags": row.get("red_flags", []),
            }
        )

    total_score = int(round(total))
    violations = session.get("violations", [])
    counts: dict[str, int] = {}
    for event in violations:
        counts[event["label"]] = counts.get(event["label"], 0) + 1

    return {
        # Carried on the card itself so a scorecard reopened later identifies the
        # candidate without depending on whatever the browser still has in memory.
        "candidate": session.get("full_name") or session.get("email") or "",
        "integrity": {
            "violation_count": len(violations),
            "flagged": bool(session.get("flagged")),
            "terminated": session.get("submit_reason") == "proctoring_terminated",
            "by_type": counts,
            "events": violations,
        },
        "total_score": total_score,
        "max_score": 100,
        "grade": _grade_letter(total_score),
        "recommendation": raw.get("recommendation") or _recommendation_for(total_score),
        "summary": raw.get("summary", ""),
        "strengths": raw.get("strengths", []),
        "improvements": raw.get("improvements", []),
        "breakdown": breakdown,
        "section_scores": _section_scores(breakdown),
        "engine": engine,
        "engine_error": error,
        "model": SCORING_MODEL if engine == "claude" else None,
    }


def _section_scores(breakdown: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    sections: dict[str, dict[str, float]] = {}
    for row in breakdown:
        bucket = sections.setdefault(row["type"], {"earned": 0.0, "weight": 0.0})
        bucket["earned"] += row["earned"]
        bucket["weight"] += row["weight"]
    for bucket in sections.values():
        bucket["earned"] = round(bucket["earned"], 1)
    return sections


def _recommendation_for(score: int) -> str:
    """Fallback recommendation when the grader did not return one (heuristic engine)."""
    if score >= 85:
        return "Strong Hire"
    if score >= 70:
        return "Hire"
    if score >= 55:
        return "Borderline"
    return "No Hire"


def _grade_letter(score: int) -> str:
    if score >= 85:
        return "A - Excellent"
    if score >= 70:
        return "B - Good"
    if score >= 55:
        return "C - Average"
    if score >= 40:
        return "D - Below expectations"
    return "E - Not suitable"
