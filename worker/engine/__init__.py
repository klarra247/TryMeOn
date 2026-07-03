"""엔진 레지스트리 — TRYON_ENGINE 환경변수로 구현체 선택."""
from __future__ import annotations

import os

from .base import TryOnEngine


def load_engine() -> TryOnEngine:
    name = os.environ.get("TRYON_ENGINE", "dummy")
    if name == "dummy":
        from .dummy import DummyTryOnEngine

        return DummyTryOnEngine()
    # Phase 1: "catvton" 구현체가 여기에 추가된다. 앱/큐/뷰어는 그대로.
    raise ValueError(f"알 수 없는 TRYON_ENGINE: {name}")
