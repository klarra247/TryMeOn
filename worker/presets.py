"""스톡 모델(마네킹 모드) 에셋 관리.

스톡 모델은 고정이므로 (Step 5):
- 전처리 산출물(마스크 등)은 모델당 딱 한 번 계산해 재사용
- 트라이온 결과는 (model_id, garment_id, angle) 키로 캐싱

디렉터리 구조:
    data/models/{model_id}/person.png        스톡 모델 사진 (직접 넣는다)
    data/models/{model_id}/preprocess/       전처리 산출물 캐시 (자동 생성)
    data/media/cache/{model_id}/{garment_id}/  트라이온 결과 캐시 (자동 생성)
"""
from __future__ import annotations

from pathlib import Path

from backend import config

DEFAULT_MODEL_ID = "mannequin-default"


def models_dir() -> Path:
    return config.DATA_DIR / "models"


def preset_person_image(model_id: str) -> Path | None:
    """스톡 모델 사진 경로. 없으면 None (더미 엔진은 실루엣으로 폴백)."""
    d = models_dir() / model_id
    matches = sorted(d.glob("person.*")) if d.exists() else []
    return matches[0] if matches else None


def preset_preprocess_dir(model_id: str) -> Path:
    d = models_dir() / model_id / "preprocess"
    d.mkdir(parents=True, exist_ok=True)
    return d


def result_cache_dir(model_id: str, garment_id: str) -> Path:
    """결과 캐시는 MEDIA_DIR 아래 — 그대로 /media/cache/... 로 서빙된다."""
    d = config.MEDIA_DIR / "cache" / model_id / garment_id
    d.mkdir(parents=True, exist_ok=True)
    return d
