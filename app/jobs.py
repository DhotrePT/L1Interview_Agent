"""Open job posts a candidate can interview for.

Each post owns a job description and a question plan: how many theory and coding
questions to draw from which bank in app/questions.py. Every interview is
1 introduction (10 marks) + 3 theory (15 each) + 3 coding (15 each) = 100.
"""
from __future__ import annotations

import random
from typing import Any

from .questions import CODING_BANKS, INTRO_QUESTION, THEORY_BANKS

# Of the 3 theory and 3 coding questions in a paper, how many must be "easy".
# This is an L1 screen for freshers, so all three are easy: the round is there to
# confirm someone can actually write working Python, not to rank the strong
# candidates against each other. Drop this to 2 to put one separating question
# back in each section.
#
# Every bank holds at least 3 easy questions, so this quota is always satisfiable;
# if a bank ever falls short the remainder is topped up from the harder pool
# rather than failing.
EASY_PER_SECTION = 3

JOBS: list[dict[str, Any]] = [
    {
        "id": "python_dev_l1",
        "active": True,
        "title": "Python Developer - L1 (Associate Software Engineer)",
        "company": "Aligned Automation",
        "location": "Pune / Hybrid",
        "experience": "0 - 2 years",
        "openings": 4,
        "tags": ["Python", "REST APIs", "Git"],
        "summary": (
            "We are hiring an entry-level Python developer to build and support automation "
            "services and data pipelines. You will write clean, tested Python, work with "
            "REST APIs and SQL, and collaborate with senior engineers on production systems."
        ),
        "responsibilities": [
            "Write and maintain Python modules, scripts and REST API endpoints.",
            "Work with structured and semi-structured data (CSV, JSON, SQL tables).",
            "Write unit tests and debug defects reported by QA.",
            "Participate in code reviews and daily stand-ups.",
            "Document what you build so the rest of the team can run it.",
        ],
        "must_have": [
            "Core Python: data types, collections, functions, comprehensions, OOP basics.",
            "Understanding of exceptions, file handling and modules/packages.",
            "Basic algorithms and complexity reasoning (loops, dicts vs lists).",
            "Git fundamentals and the ability to explain your own code clearly.",
        ],
        "good_to_have": [
            "FastAPI / Flask, pandas, pytest.",
            "SQL joins and aggregations.",
            "Docker basics, CI/CD exposure.",
        ],
        "plan": {
            "theory": [("python_core", 3)],
            "coding": [("python_core", 3)],
        },
    },
    {
        "id": "data_engineer_l1",
        "active": True,
        "title": "Data Engineer - L1 (Python + SQL)",
        "company": "Aligned Automation",
        "location": "Pune / Hybrid",
        "experience": "0 - 2 years",
        "openings": 2,
        "tags": ["Python", "SQL", "pandas"],
        "summary": (
            "Join the data team to move, clean and reconcile data between client systems. "
            "You will write Python transformations, query relational databases and make sure "
            "the numbers that reach a dashboard are the numbers that left the source."
        ),
        "responsibilities": [
            "Build and maintain ingestion scripts for CSV, JSON and database sources.",
            "Write SQL for extraction, aggregation and reconciliation checks.",
            "Clean and validate messy real-world data, and report what you had to drop.",
            "Automate daily loads and investigate failures when they break.",
            "Keep transformation logic documented and reviewable.",
        ],
        "must_have": [
            "Core Python with dicts, lists and file handling.",
            "SQL: joins, GROUP BY, aggregation, and reading a query plan at a basic level.",
            "Careful handling of nulls, duplicates and type conversion.",
            "Ability to explain a transformation end to end.",
        ],
        "good_to_have": [
            "pandas, Airflow or any scheduler.",
            "Cloud storage (S3 / Blob), Snowflake or PostgreSQL.",
            "Basic data modelling (fact / dimension).",
        ],
        "plan": {
            "theory": [("sql_data", 2), ("python_core", 1)],
            "coding": [("sql_data", 2), ("python_core", 1)],
        },
    },
    {
        "id": "automation_qa_l1",
        "active": True,
        "title": "Automation QA Engineer - L1 (Python)",
        "company": "Aligned Automation",
        "location": "Pune / Remote",
        "experience": "0 - 2 years",
        "openings": 3,
        "tags": ["Python", "pytest", "API testing"],
        "summary": (
            "Help us keep releases safe. You will write automated tests in Python for REST "
            "APIs and internal tools, chase down flaky failures, and make the test suite "
            "something the team actually trusts."
        ),
        "responsibilities": [
            "Write and maintain automated API and regression tests in pytest.",
            "Reproduce, isolate and report defects with clear steps.",
            "Keep the suite green: fix or quarantine flaky tests, don't ignore them.",
            "Add logging and diagnostics so failures explain themselves.",
            "Work with developers on what is worth testing and what is not.",
        ],
        "must_have": [
            "Core Python: functions, exceptions, string and file handling.",
            "Understanding of unit vs integration tests and what a mock is for.",
            "HTTP fundamentals: methods, status codes, headers, JSON payloads.",
            "Ability to explain why a test failed, not just that it failed.",
        ],
        "good_to_have": [
            "pytest fixtures and parametrize, requests, Postman.",
            "Selenium or Playwright.",
            "CI pipelines (GitHub Actions, Jenkins).",
        ],
        "plan": {
            "theory": [("automation", 2), ("python_core", 1)],
            "coding": [("automation", 2), ("python_core", 1)],
        },
    },
]

JOBS_BY_ID: dict[str, dict[str, Any]] = {job["id"]: job for job in JOBS}


def get_job(job_id: str) -> dict[str, Any] | None:
    return JOBS_BY_ID.get(job_id)


def job_description(job: dict[str, Any]) -> dict[str, Any]:
    """The candidate-facing JD - everything except the internal question plan."""
    return {key: value for key, value in job.items() if key != "plan"} | {
        "interview_format": [
            "Round L1 - 30 minutes, automated, recorded and proctored.",
            "1 introduction + 3 theory questions + 3 coding questions.",
            "Every answer must also be explained out loud on camera.",
            "A scorecard out of 100 is generated at the end.",
        ]
    }


def open_posts() -> list[dict[str, Any]]:
    """Short cards for the candidate dashboard."""
    return [
        {
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "experience": job["experience"],
            "openings": job["openings"],
            "tags": job["tags"],
            "summary": job["summary"],
        }
        for job in JOBS
        if job["active"]
    ]


def build_question_set(job_id: str, seed: str | None = None) -> list[dict[str, Any]]:
    """Intro first, then the theory questions, then the coding questions."""
    job = JOBS_BY_ID[job_id]
    rng = random.Random(seed)

    def draw(banks: dict[str, list[dict[str, Any]]], plan: list[tuple[str, int]]):
        """Fill the plan, spending the easy quota first so a paper is mostly easy.

        The plan decides which banks (it is what makes the Data Engineer paper lean
        SQL); the quota decides how hard the questions are. If a bank runs out of one
        difficulty the remainder is topped up from the other, so a thin bank degrades
        to "as easy as it can be" rather than raising an error.
        """
        picked: list[dict[str, Any]] = []
        easy_left = EASY_PER_SECTION

        for bank_name, count in plan:
            pool = banks[bank_name]
            easy = [q for q in pool if q.get("difficulty", "medium") == "easy"]
            harder = [q for q in pool if q.get("difficulty", "medium") != "easy"]

            take_easy = min(count, easy_left, len(easy))
            chosen = rng.sample(easy, take_easy)
            easy_left -= take_easy

            shortfall = count - len(chosen)
            if shortfall:
                from_harder = rng.sample(harder, min(shortfall, len(harder)))
                chosen.extend(from_harder)

            if len(chosen) < count:  # bank too thin - top up from whatever is left
                taken = {q["id"] for q in chosen}
                spare = [q for q in pool if q["id"] not in taken]
                chosen.extend(rng.sample(spare, count - len(chosen)))

            picked.extend(chosen)

        rng.shuffle(picked)
        return picked

    questions: list[dict[str, Any]] = [dict(INTRO_QUESTION)]
    questions.extend(dict(q) for q in draw(THEORY_BANKS, job["plan"]["theory"]))
    questions.extend(dict(q) for q in draw(CODING_BANKS, job["plan"]["coding"]))

    for index, question in enumerate(questions, start=1):
        question["number"] = index
    return questions


def public_question(question: dict[str, Any]) -> dict[str, Any]:
    """The candidate-facing view - expectations stay on the server."""
    return {
        "id": question["id"],
        "number": question["number"],
        "type": question["type"],
        "title": question["title"],
        "prompt": question["prompt"],
        "weight": question["weight"],
        "starter_code": question.get("starter_code", ""),
        "suggested_minutes": question.get("suggested_minutes", 4),
    }
