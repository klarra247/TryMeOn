"""상품 카탈로그 — Phase 0 시드 데이터.

실제 점주 온보딩(업로드→정규화)은 Phase 2. 지금은 첫 실행 시
PIL 로 평면 의류 목업 이미지를 생성해 로컬에 시드한다.
(점주 입력 = 평면 옷 사진 앞·뒤 라는 제약을 그대로 흉내낸다.)
"""
from __future__ import annotations

import json

from PIL import Image, ImageDraw

from shared.schemas import GarmentAssets, Product

from . import config

CATALOG_JSON = config.DATA_DIR / "catalog.json"

_SEED = [
    ("tshirt-coral", "코랄 티셔츠", 29000, (240, 128, 110), "tshirt", ["상의", "캐주얼"]),
    ("tshirt-navy", "네이비 티셔츠", 31000, (48, 68, 120), "tshirt", ["상의", "베이직"]),
    ("hoodie-sage", "세이지 후드", 59000, (148, 170, 138), "hoodie", ["상의", "아우터"]),
    ("dress-plum", "플럼 원피스", 78000, (120, 62, 110), "dress", ["원피스"]),
    ("shirt-sand", "샌드 셔츠", 45000, (208, 186, 150), "shirt", ["상의", "포멀"]),
]


def _draw_garment(kind: str, color: tuple[int, int, int], back: bool) -> Image.Image:
    """평면 의류 목업. 뒷면은 톤을 살짝 어둡게 + 넥라인 단순화."""
    w, h = 480, 600
    img = Image.new("RGB", (w, h), (245, 245, 247))
    d = ImageDraw.Draw(img)
    c = tuple(max(0, ch - 25) for ch in color) if back else color
    cx = w // 2

    if kind in ("tshirt", "shirt", "hoodie"):
        body_top, body_bot = 150, 470
        d.polygon(  # 몸통
            [(cx - 110, body_top), (cx + 110, body_top),
             (cx + 130, body_bot), (cx - 130, body_bot)], fill=c)
        d.polygon(  # 왼소매
            [(cx - 110, body_top), (cx - 200, body_top + 70),
             (cx - 165, body_top + 130), (cx - 100, body_top + 60)], fill=c)
        d.polygon(  # 오른소매
            [(cx + 110, body_top), (cx + 200, body_top + 70),
             (cx + 165, body_top + 130), (cx + 100, body_top + 60)], fill=c)
        if not back:
            d.ellipse([cx - 45, body_top - 22, cx + 45, body_top + 28],
                      fill=(245, 245, 247))  # 넥라인
        if kind == "hoodie":
            d.ellipse([cx - 70, body_top - 55, cx + 70, body_top + 40], fill=c)
            if not back:
                d.ellipse([cx - 40, body_top - 30, cx + 40, body_top + 30],
                          fill=tuple(max(0, ch - 40) for ch in c))
    else:  # dress
        d.polygon(
            [(cx - 85, 140), (cx + 85, 140), (cx + 150, 520), (cx - 150, 520)], fill=c)
        d.polygon([(cx - 85, 140), (cx - 150, 200), (cx - 120, 240), (cx - 78, 185)], fill=c)
        d.polygon([(cx + 85, 140), (cx + 150, 200), (cx + 120, 240), (cx + 78, 185)], fill=c)
        if not back:
            d.ellipse([cx - 38, 122, cx + 38, 165], fill=(245, 245, 247))

    return img


def seed_catalog(force: bool = False) -> list[Product]:
    """카탈로그가 없으면 목업 의류 이미지 + catalog.json 을 생성."""
    config.ensure_dirs()
    if CATALOG_JSON.exists() and not force:
        return load_catalog()

    products: list[Product] = []
    for pid, name, price, color, kind, tags in _SEED:
        front_rel = f"catalog/{pid}_front.png"
        back_rel = f"catalog/{pid}_back.png"
        _draw_garment(kind, color, back=False).save(config.MEDIA_DIR / front_rel)
        _draw_garment(kind, color, back=True).save(config.MEDIA_DIR / back_rel)
        products.append(Product(
            id=pid, name=name, price=price,
            description=f"{name} — Phase 0 시드 상품",
            garment=GarmentAssets(front=f"/media/{front_rel}", back=f"/media/{back_rel}"),
            tags=tags,
        ))

    CATALOG_JSON.write_text(
        json.dumps([p.model_dump() for p in products], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return products


def load_catalog() -> list[Product]:
    if not CATALOG_JSON.exists():
        return seed_catalog()
    raw = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    return [Product.model_validate(p) for p in raw]


def get_product(product_id: str) -> Product | None:
    return next((p for p in load_catalog() if p.id == product_id), None)
