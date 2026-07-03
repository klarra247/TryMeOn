"""TryOnEngine 인터페이스 (설계 원칙 1: 엔진은 인터페이스 뒤에).

이 계약만 고정하면 뒤 모델은 이미지→멀티뷰→영상→3D 로 갈아끼워도
앱은 안 건드린다. Phase 1의 CatVTON 워커는 이 ABC 의 구현체 하나다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.schemas import EngineInput


@dataclass
class EngineOutput:
    """엔진이 out_dir 에 쓴 산출물의 목록. URL 변환은 태스크 계층 몫."""
    views: list[tuple[int, Path]]          # (angle, 이미지 파일 경로)
    clip: Path | None = None               # 미래: 회전 영상
    asset3d: Path | None = None            # 미래: 3D 에셋
    meta: dict[str, Any] = field(default_factory=dict)


class TryOnEngine(ABC):
    """입력: EngineInput(person|preset, garment_assets, options) → 출력: 미디어 번들."""

    name: str = "base"

    @abstractmethod
    def run(self, inp: EngineInput, out_dir: Path) -> EngineOutput:
        """트라이온을 수행하고 산출물을 out_dir 에 저장한다."""
        raise NotImplementedError
