"""워커 쪽 미디어 경로 유틸.

Phase 1 토폴로지: API·워커·미디어가 같은 머신(GPU pod)에 있으므로
/media/... URL ↔ 로컬 경로 변환은 단순 매핑이다.
워커가 백엔드와 파일시스템을 공유하지 않게 되는 시점에
이 함수만 다운로드(HTTP/S3) 구현으로 바꾸면 된다.
"""
from __future__ import annotations

from pathlib import Path

from backend import config


def resolve_media_path(url_or_path: str) -> Path:
    if url_or_path.startswith("/media/"):
        return config.MEDIA_DIR / url_or_path.removeprefix("/media/")
    return Path(url_or_path)
