"""의류 전처리 — 맥에서 CPU 로 돌아가는 가벼운 조각 (Phase 0 로컬 연습분).

배경 제거는 rembg (CPU/onnxruntime) 사용. 설치는 옵셔널:
    uv sync --extra preprocess
미설치 시 경고 후 원본을 그대로 반환한다 (파이프라인은 안 끊김).

Phase 2 점주 온보딩(업로드→자동 배경제거→정규화)의 첫 조각이 된다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)


def remove_background(src: Path, dst: Path) -> Path:
    """의류 사진 배경 제거. rembg 미설치 시 원본 복사로 폴백."""
    img = Image.open(src).convert("RGBA")
    try:
        from rembg import remove  # type: ignore[import-not-found]

        out = remove(img)
    except ImportError:
        log.warning("rembg 미설치 — 배경 제거 건너뜀 (uv sync --extra preprocess)")
        out = img
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return dst


def normalize_garment(src: Path, dst: Path, size: tuple[int, int] = (768, 1024)) -> Path:
    """모델 입력 규격으로 정규화: 배경 제거 + 여백 포함 리사이즈."""
    removed = dst.parent / f"_nobg_{src.stem}.png"
    remove_background(src, removed)

    img = Image.open(removed).convert("RGBA")
    img.thumbnail(size)
    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    canvas.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2), img)
    canvas.save(dst)
    removed.unlink(missing_ok=True)
    return dst
