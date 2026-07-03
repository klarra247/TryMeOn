"""엔진 레지스트리 — TRYON_ENGINE 환경변수로 구현체 선택."""
from __future__ import annotations

import os

from .base import TryOnEngine


def load_engine() -> TryOnEngine:
    name = os.environ.get("TRYON_ENGINE", "dummy")
    if name == "dummy":
        from .dummy import DummyTryOnEngine

        return DummyTryOnEngine()
    if name == "catvton":
        from .catvton import CatVTONEngine

        return CatVTONEngine()
    raise ValueError(f"알 수 없는 TRYON_ENGINE: {name}")
