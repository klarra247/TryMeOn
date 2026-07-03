"""SQLite 잡 스토어. TryOnResult 번들 전체를 JSON 컬럼으로 보관.

백엔드(API)와 워커가 같은 DB 파일을 공유한다 — Phase 0 로컬 전제.
Phase 1에서 워커가 원격 GPU로 가면 이 계층만 Postgres/오브젝트 스토리지로 교체.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from shared.schemas import JobStatus, TryOnResult

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id         TEXT PRIMARY KEY,
    status     TEXT NOT NULL,
    result     TEXT NOT NULL,  -- TryOnResult JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_job(result: TryOnResult) -> None:
    with _conn() as c:
        c.execute(
            """INSERT INTO jobs (id, status, result, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 status = excluded.status,
                 result = excluded.result,
                 updated_at = excluded.updated_at""",
            (result.id, result.status.value, result.model_dump_json(), _now(), _now()),
        )


def get_job(job_id: str) -> TryOnResult | None:
    with _conn() as c:
        row = c.execute("SELECT result FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return TryOnResult.model_validate_json(row[0]) if row else None


def set_status(job_id: str, status: JobStatus, error: str | None = None) -> TryOnResult | None:
    job = get_job(job_id)
    if job is None:
        return None
    job.status = status
    if error is not None:
        job.error = error
    save_job(job)
    return job
