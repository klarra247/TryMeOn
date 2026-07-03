"""작업 큐 플러밍 (설계 원칙 5: 모델 = 원격 워커).

기본은 Redis + RQ. 백엔드는 잡 ID만 큐에 넣고, 워커 프로세스가
worker.tasks.run_tryon 을 실행한다. Redis 가 없는 환경(데모/테스트)을 위해
thread / sync 폴백을 둔다 — 어느 모드든 워커 코드는 동일하다.
"""
from __future__ import annotations

import logging
import threading

from . import config

log = logging.getLogger(__name__)

_resolved_mode: str | None = None


def _redis_available() -> bool:
    try:
        import redis

        redis.Redis.from_url(config.REDIS_URL).ping()
        return True
    except Exception:
        return False


def queue_mode() -> str:
    global _resolved_mode
    if _resolved_mode is None:
        mode = config.QUEUE_MODE
        if mode == "auto":
            mode = "redis" if _redis_available() else "thread"
            if mode == "thread":
                log.warning("Redis 미접속 — thread 큐 모드로 폴백 (데모 전용)")
        _resolved_mode = mode
    return _resolved_mode


def enqueue_tryon(job_id: str) -> None:
    mode = queue_mode()
    if mode == "redis":
        import redis
        from rq import Queue

        q = Queue(config.RQ_QUEUE_NAME, connection=redis.Redis.from_url(config.REDIS_URL))
        q.enqueue("worker.tasks.run_tryon", job_id, job_timeout=600)
    elif mode == "thread":
        from worker.tasks import run_tryon

        threading.Thread(target=run_tryon, args=(job_id,), daemon=True).start()
    elif mode == "sync":
        from worker.tasks import run_tryon

        run_tryon(job_id)
    else:
        raise ValueError(f"알 수 없는 QUEUE_MODE: {mode}")
