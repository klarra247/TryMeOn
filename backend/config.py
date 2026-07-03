"""경로/환경 설정. 저장은 로컬 파일 + SQLite 메타로 충분 (Phase 0)."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("TRYMEON_DATA_DIR", REPO_ROOT / "data"))
MEDIA_DIR = DATA_DIR / "media"            # /media 로 서빙되는 루트
CATALOG_MEDIA_DIR = MEDIA_DIR / "catalog" # 의류 시드 이미지
JOBS_MEDIA_DIR = MEDIA_DIR / "jobs"       # 잡별 산출물 (person 원본, views)
DB_PATH = DATA_DIR / "trymeon.sqlite3"

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# 키오스크 프론트 오리진. 원격 GPU pod 토폴로지(Phase 1 Step 4)에서는
# 맥의 dev 서버가 pod API 를 직접 치므로 여기에 추가하거나 "*" 로 연다.
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
RQ_QUEUE_NAME = "tryon"

# 큐 모드:
#   redis  — Redis + RQ (프로덕션 구조, 기본. 워커 프로세스 별도 실행)
#   thread — 백엔드 프로세스 안의 스레드로 실행 (Redis 없이 데모용)
#   sync   — 요청 안에서 동기 실행 (테스트 전용)
#   auto   — redis 접속 가능하면 redis, 아니면 thread 로 폴백
QUEUE_MODE = os.environ.get("QUEUE_MODE", "auto")

# 더미 엔진이 생성하는 앵글 (Phase 4에서 0/±45/±90/180 로 확장)
DEFAULT_ANGLES = [-45, 0, 45]


def ensure_dirs() -> None:
    for d in (DATA_DIR, MEDIA_DIR, CATALOG_MEDIA_DIR, JOBS_MEDIA_DIR):
        d.mkdir(parents=True, exist_ok=True)
