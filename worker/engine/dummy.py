"""더미 트라이온 엔진 — 모델 없이 전 루프를 돌리기 위한 Phase 0 구현체.

앵글별 placeholder 를 실시간 생성한다:
- mannequin 모드: 회색 마네킹 실루엣 + 의류 이미지 합성
- user 모드: 촬영한 사진을 배경으로 깔고 의류 이미지 합성
  (진짜 합성이 아니라 데이터 흐름 검증용 — Phase 1에서 CatVTON 으로 교체)
앵글마다 마네킹/의류를 살짝 기울여 "이산 회전" 느낌을 흉내낸다.
"""
from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from shared.schemas import EngineInput

from .base import EngineOutput, TryOnEngine

W, H = 600, 800
SIMULATED_LATENCY_SEC = 0.7  # 앵글당 — 폴링/로딩 UX 를 실제처럼 굴리기 위함


def _draw_mannequin(d: ImageDraw.ImageDraw, angle: int) -> None:
    """회색 마네킹 실루엣. angle 에 따라 수평으로 살짝 이동시켜 회전 흉내."""
    cx = W // 2 + int(angle * 0.6)
    gray = (168, 170, 176)
    d.ellipse([cx - 42, 70, cx + 42, 160], fill=gray)                     # 머리
    d.rectangle([cx - 14, 158, cx + 14, 190], fill=gray)                  # 목
    d.polygon([(cx - 95, 190), (cx + 95, 190), (cx + 75, 480), (cx - 75, 480)], fill=gray)  # 몸통
    d.polygon([(cx - 60, 480), (cx - 15, 480), (cx - 25, 740), (cx - 62, 740)], fill=gray)  # 왼다리
    d.polygon([(cx + 15, 480), (cx + 60, 480), (cx + 62, 740), (cx + 25, 740)], fill=gray)  # 오른다리


def _key_out_background(img: Image.Image, threshold: int = 235) -> Image.Image:
    """시드 목업의 밝은 단색 배경을 투명 처리 (Phase 2 배경 제거의 초저가 흉내)."""
    img = img.convert("RGBA")
    px = img.getdata()
    img.putdata([
        (r, g, b, 0) if r > threshold and g > threshold and b > threshold else (r, g, b, a)
        for r, g, b, a in px
    ])
    return img


def _resolve_garment_path(url_or_path: str) -> Path:
    """가먼트 asset URL(/media/...) → 워커 로컬 경로. Phase 0은 파일시스템 공유 전제."""
    from backend import config

    if url_or_path.startswith("/media/"):
        return config.MEDIA_DIR / url_or_path.removeprefix("/media/")
    return Path(url_or_path)


class DummyTryOnEngine(TryOnEngine):
    name = "dummy"

    def run(self, inp: EngineInput, out_dir: Path) -> EngineOutput:
        angles = inp.options.get("angles", [-45, 0, 45])
        garment_path = _resolve_garment_path(inp.garment.front)
        garment = (
            _key_out_background(Image.open(garment_path)) if garment_path.exists() else None
        )

        person_bg = None
        if inp.person_image_path:
            p = Path(inp.person_image_path)
            if p.exists():
                person_bg = Image.open(p).convert("RGB")

        views: list[tuple[int, Path]] = []
        for i, angle in enumerate(angles):
            time.sleep(SIMULATED_LATENCY_SEC)
            img = self._render(angle, garment, person_bg)
            path = out_dir / f"view_{i}_{angle:+d}.png"
            img.save(path)
            views.append((angle, path))

        return EngineOutput(views=views, meta={"engine": self.name, "angles": angles})

    def _render(self, angle: int, garment: Image.Image | None,
                person_bg: Image.Image | None) -> Image.Image:
        img = Image.new("RGB", (W, H), (235, 236, 240))
        d = ImageDraw.Draw(img)

        if person_bg is not None:
            bg = person_bg.copy()
            bg.thumbnail((W, H))
            bg = bg.filter(ImageFilter.GaussianBlur(1))
            img.paste(bg, ((W - bg.width) // 2, (H - bg.height) // 2))
            d = ImageDraw.Draw(img)
        else:
            _draw_mannequin(d, angle)

        if garment is not None:
            g = garment.copy()
            # 앵글에 따라 의류를 살짝 좁혀 붙여 회전한 척
            squeeze = max(0.55, 1 - abs(angle) / 180)
            g = g.resize((int(420 * squeeze), 520))
            g = g.rotate(-angle * 0.08, expand=False)
            gx = (W - g.width) // 2 + int(angle * 0.6)
            img.paste(g, (gx, 130), g)
            d = ImageDraw.Draw(img)

        label = f"{angle:+d}°  (dummy)"
        d.rectangle([16, H - 56, 16 + 9 * len(label) + 16, H - 20], fill=(30, 30, 34))
        d.text((26, H - 48), label, fill=(240, 240, 240))
        return img
