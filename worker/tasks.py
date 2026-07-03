"""RQ 태스크: 잡 로드 → 엔진 실행 → 미디어 번들로 DB 업데이트.

이 파일은 어떤 큐 모드(redis/thread/sync)에서도 동일하게 실행된다.
Phase 1에서 워커가 클라우드 GPU 로 가도 이 흐름은 유지된다 —
엔진 구현체와 스토리지 계층만 바뀐다.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from backend import catalog, config, db
from shared.schemas import EngineInput, JobStatus, TryOnMode, ViewImage

from .engine import load_engine

log = logging.getLogger(__name__)

PRESET_MODEL_ID = "mannequin-default"  # Phase 2에서 스톡 모델 세트로 확장


def _find_person_image(job_dir: Path) -> Path | None:
    matches = sorted(job_dir.glob("person.*"))
    return matches[0] if matches else None


def run_tryon(job_id: str) -> None:
    job = db.get_job(job_id)
    if job is None:
        log.error("job %s 없음", job_id)
        return

    db.set_status(job_id, JobStatus.PROCESSING)
    started = time.monotonic()
    try:
        product = catalog.get_product(job.product_id)
        if product is None:
            raise RuntimeError(f"product {job.product_id} 없음")

        job_dir = config.JOBS_MEDIA_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        person_path = _find_person_image(job_dir) if job.mode == TryOnMode.USER else None
        if job.mode == TryOnMode.USER and person_path is None:
            raise RuntimeError("user 모드인데 person 이미지가 없음")

        engine = load_engine()
        inp = EngineInput(
            person_image_path=str(person_path) if person_path else None,
            preset_model_id=None if person_path else PRESET_MODEL_ID,
            garment=product.garment,
            options={"angles": config.DEFAULT_ANGLES},
        )
        out = engine.run(inp, job_dir)

        job.views = [
            ViewImage(angle=angle, url=f"/media/jobs/{job_id}/{path.name}")
            for angle, path in out.views
        ]
        job.clip = f"/media/jobs/{job_id}/{out.clip.name}" if out.clip else None
        job.asset3d = f"/media/jobs/{job_id}/{out.asset3d.name}" if out.asset3d else None
        job.meta = {**job.meta, **out.meta,
                    "elapsed_sec": round(time.monotonic() - started, 2)}
        job.status = JobStatus.DONE
        db.save_job(job)
        log.info("job %s done (%.1fs, %d views)", job_id,
                 time.monotonic() - started, len(job.views))
    except Exception as e:  # noqa: BLE001 — 실패를 번들 상태로 기록
        log.exception("job %s failed", job_id)
        db.set_status(job_id, JobStatus.FAILED, error=str(e))
