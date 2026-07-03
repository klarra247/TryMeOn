"""TryMeOn 공유 스키마 — 이 파일이 계약의 단일 진실 출처(canonical).

설계 원칙(docs/DESIGN.md §7):
- 결과 = 미디어 번들. views 배열 + clip/asset3d 옵셔널.
  뷰어는 처음부터 N개 앵글 전제 (지금은 1~3장만 채워도 동작).
- 엔진은 인터페이스 뒤에 (worker/engine/base.py 가 이 타입들을 사용).
- frontend 는 shared/types.ts (이 파일의 미러)를 import 한다.
  스키마를 바꾸면 두 파일을 함께 바꿀 것.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class TryOnMode(str, Enum):
    MANNEQUIN = "mannequin"  # 스톡 모델 착용 (사전 캐싱 대상, Phase 2)
    USER = "user"            # 손님 정면 사진 1장 착용 (실시간 경로)


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class ViewImage(BaseModel):
    """이산 회전의 한 앵글. angle 은 정면 0°, 좌 -, 우 + (도 단위)."""
    angle: int
    url: str


class TryOnResult(BaseModel):
    """버전 있는 미디어 번들 — 단일 PNG가 아님.

    Phase 0~1: views 1~3장.
    Phase 4:   views 0°/±45°/±90°/180°.
    Phase 5:   clip(회전 영상) / asset3d(3D 에셋) 채움. 앱/뷰어는 안 바뀜.
    """
    schema_version: int = SCHEMA_VERSION
    id: str
    status: JobStatus
    mode: TryOnMode
    product_id: str
    views: list[ViewImage] = Field(default_factory=list)
    clip: str | None = None      # 미래: 영상 VTON 클립 URL
    asset3d: str | None = None   # 미래: 3D 에셋(GS/메시) URL
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)  # engine 이름, 소요시간 등


class GarmentAssets(BaseModel):
    """점주가 올리는 평면 옷 사진. 데이터 과수집 원칙: 뒤/옆도 슬롯 확보."""
    front: str                 # 필수
    back: str | None = None
    side: str | None = None


class Product(BaseModel):
    id: str
    name: str
    price: int
    description: str = ""
    garment: GarmentAssets
    tags: list[str] = Field(default_factory=list)


class EngineInput(BaseModel):
    """TryOnEngine 입력 계약 (설계 원칙 1).

    person_image_path 와 preset_model_id 중 정확히 하나가 채워진다.
    경로는 워커 로컬 파일시스템 기준 (모델 = 원격 워커 원칙 하에서
    스토리지 계층이 URL→로컬 경로 변환을 책임진다).
    """
    person_image_path: str | None = None   # user 모드: 정면 전신 사진
    preset_model_id: str | None = None     # mannequin 모드: 스톡 모델 ID
    garment: GarmentAssets
    options: dict[str, Any] = Field(default_factory=dict)  # 앵글 수, 해상도 등


class PreprocessArtifacts(BaseModel):
    """전처리 산출물 스키마 (설계 원칙 3: 전부 저장).

    전처리 = cloth-agnostic 마스크 생성. Phase 0은 인터페이스만 확정,
    무거운 구현(SCHP+DensePose)은 Phase 1 클라우드 GPU 몫.
    """
    agnostic_mask: str            # CatVTON 이 요구하는 핵심 산출물
    parse_map: str | None = None  # SCHP 휴먼 파싱 맵
    pose: str | None = None       # 포즈 키포인트
    densepose: str | None = None  # DensePose IUV
