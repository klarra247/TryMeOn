"""TryMeOn API 서버 (FastAPI).

엔드포인트:
- GET  /api/products          상품 목록 (키오스크 첫 화면)
- GET  /api/products/{id}     상품 상세
- POST /api/tryon             트라이온 잡 enqueue (multipart)
- GET  /api/tryon/{id}        잡 폴링 → TryOnResult 미디어 번들
- /media/*                    생성물/카탈로그 이미지 정적 서빙

개인정보 원칙(docs/DESIGN.md §8): 사용자 사진은 잡 디렉터리에만 저장되는
세션 단위 임시 데이터다. 영구 보관/동의 흐름은 파일럿(Phase 2) 전에 붙인다.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.schemas import JobStatus, Product, TryOnMode, TryOnResult

from . import catalog, config, db, queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    db.init_db()
    catalog.seed_catalog()
    yield


app = FastAPI(title="TryMeOn API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config.ensure_dirs()
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")


@app.get("/api/products", response_model=list[Product])
def list_products() -> list[Product]:
    return catalog.load_catalog()


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return product


@app.post("/api/tryon", response_model=TryOnResult)
async def create_tryon(
    product_id: str = Form(...),
    mode: TryOnMode = Form(...),
    person_image: UploadFile | None = File(None),
) -> TryOnResult:
    product = catalog.get_product(product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    if mode == TryOnMode.USER and person_image is None:
        raise HTTPException(422, "user 모드는 person_image 가 필요합니다")

    job_id = uuid.uuid4().hex[:12]
    job_dir: Path = config.JOBS_MEDIA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    if person_image is not None:
        suffix = Path(person_image.filename or "person.png").suffix or ".png"
        (job_dir / f"person{suffix}").write_bytes(await person_image.read())

    result = TryOnResult(
        id=job_id, status=JobStatus.QUEUED, mode=mode, product_id=product_id,
        meta={"queue_mode": queue.queue_mode()},
    )
    db.save_job(result)
    queue.enqueue_tryon(job_id)
    return result


@app.get("/api/tryon/{job_id}", response_model=TryOnResult)
def get_tryon(job_id: str) -> TryOnResult:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job
