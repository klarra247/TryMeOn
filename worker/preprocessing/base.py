"""전처리 모듈 인터페이스 — Phase 0에서 계약만 확정 (Step 7).

전처리 = cloth-agnostic 마스크 생성:
    사람 사진 → 휴먼 파싱(SCHP) + DensePose → agnostic mask

SCHP+DensePose 는 CUDA/Detectron2 에 묶여 있어 맥 로컬에선 무리 —
무거운 구현체는 Phase 1에서 클라우드 GPU 컨테이너로 만든다.
설계 원칙 3(데이터 과수집): 산출물(parse/pose/densepose/mask)은 전부 저장.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from shared.schemas import PreprocessArtifacts


class PersonPreprocessor(ABC):
    """입력: 정면 전신 사진 → 출력: PreprocessArtifacts (마스크 + 부산물)."""

    name: str = "base"

    @abstractmethod
    def run(self, person_image: Path, out_dir: Path) -> PreprocessArtifacts:
        raise NotImplementedError


class CloudMaskPreprocessor(PersonPreprocessor):
    """Phase 1 자리표시자: SCHP + DensePose 기반 마스크 생성 (클라우드 GPU).

    맥/로컬에서는 절대 구현하지 않는다 — 컨테이너화해서 GPU 워커에 태운다.
    """

    name = "schp-densepose"

    def run(self, person_image: Path, out_dir: Path) -> PreprocessArtifacts:
        raise NotImplementedError(
            "SCHP+DensePose 마스크 생성은 Phase 1 (클라우드 GPU 컨테이너) 작업입니다"
        )
