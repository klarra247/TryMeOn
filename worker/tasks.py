"""RQ 태스크: 잡 로드 → (캐시 확인) → 엔진 실행 → 미디어 번들로 DB 업데이트.

이 파일은 어떤 큐 모드(redis/thread/sync)에서도, 어떤 엔진(dummy/catvton)
에서도 동일하게 실행된다.

마네킹 모드 캐싱 (Step 5): 스톡 모델·의류·앵글이 같으면 결과가 같으므로
(model_id, garment_id) 캐시 디렉터리에 번들을 저장하고 재사용한다.
점주가 옷을 등록하는 순간 백그라운드로 미리 돌려두면 키오스크에선 대기 0초.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from backend import catalog, config, db
from shared.schemas import EngineInput, JobStatus, Product, TryOnMode, ViewImage

from . import presets
from .engine import load_engine
from .engine.base import EngineOutput

log = logging.getLogger(__name__)

# 상품 태그 → CatVTON AutoMasker mask_type
_CLOTH_TYPE_BY_TAG = {"상의": "upper", "하의": "lower", "원피스": "overall", "아우터": "upper"}


def cloth_type_for(product: Product) -> str:
    for tag in product.tags:
        if tag in _CLOTH_TYPE_BY_TAG:
            return _CLOTH_TYPE_BY_TAG[tag]
    return "upper"


def _find_person_image(job_dir: Path) -> Path | None:
    matches = sorted(job_dir.glob("person.*"))
    return matches[0] if matches else None


def _media_url(path: Path) -> str:
    return f"/media/{path.relative_to(config.MEDIA_DIR).as_posix()}"


def _bundle_from_output(out: EngineOutput) -> dict:
    return {
        "views": [{"angle": angle, "url": _media_url(p)} for angle, p in out.views],
        "clip": _media_url(out.clip) if out.clip else None,
        "asset3d": _media_url(out.asset3d) if out.asset3d else None,
        "meta": out.meta,
    }


def _run_engine(job_mode: TryOnMode, product: Product,
                person_path: Path | None, out_dir: Path) -> dict:
    engine = load_engine()
    inp = EngineInput(
        person_image_path=str(person_path) if person_path else None,
        preset_model_id=None if person_path else presets.DEFAULT_MODEL_ID,
        garment=product.garment,
        options={
            "angles": config.DEFAULT_ANGLES,
            "cloth_type": cloth_type_for(product),
        },
    )
    return _bundle_from_output(engine.run(inp, out_dir))


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

        if job.mode == TryOnMode.MANNEQUIN:
            cache_dir = presets.result_cache_dir(presets.DEFAULT_MODEL_ID, product.id)
            bundle_file = cache_dir / "bundle.json"
            if bundle_file.exists():
                bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
                bundle["meta"] = {**bundle.get("meta", {}), "cache_hit": True}
            else:
                bundle = _run_engine(job.mode, product, None, cache_dir)
                bundle_file.write_text(
                    json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
                bundle["meta"] = {**bundle["meta"], "cache_hit": False}
        else:
            job_dir = config.JOBS_MEDIA_DIR / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            person_path = _find_person_image(job_dir)
            if person_path is None:
                raise RuntimeError("user 모드인데 person 이미지가 없음")
            bundle = _run_engine(job.mode, product, person_path, job_dir)

        job.views = [ViewImage(**v) for v in bundle["views"]]
        job.clip = bundle["clip"]
        job.asset3d = bundle["asset3d"]
        job.meta = {**job.meta, **bundle["meta"],
                    "elapsed_sec": round(time.monotonic() - started, 2)}
        job.status = JobStatus.DONE
        db.save_job(job)
        log.info("job %s done (%.1fs, %d views, cache_hit=%s)", job_id,
                 time.monotonic() - started, len(job.views),
                 bundle["meta"].get("cache_hit"))
    except Exception as e:  # noqa: BLE001 — 실패를 번들 상태로 기록
        log.exception("job %s failed", job_id)
        db.set_status(job_id, JobStatus.FAILED, error=str(e))
