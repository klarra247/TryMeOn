"""의류 × 사람 격자 배치 트라이온 — 실패 모드 관찰용 (Phase 1 Step 6).

엔진을 직접 호출한다 (API/큐 우회) — pod 에서 빠르게 도는 게 목적.
결과는 out/batch/ 에 저장되고 index.html 콘택트 시트로 한눈에 본다.
관찰 기록은 docs/FAILURE_MODES.md 에.

사용:
    TRYON_ENGINE=catvton python experiments/batch_tryon.py \
        --garments data/test/garments --persons data/test/persons
    (GPU 없이 파이프라인만 점검: TRYON_ENGINE=dummy 로 실행)
"""
from __future__ import annotations

import argparse
import html
import time
from pathlib import Path

from shared.schemas import EngineInput, GarmentAssets
from worker.engine import load_engine

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def images_in(d: Path) -> list[Path]:
    return sorted(p for p in d.iterdir() if p.suffix.lower() in IMG_EXTS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--garments", type=Path, required=True)
    ap.add_argument("--persons", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out" / "batch")
    ap.add_argument("--cloth-type", default="upper")
    args = ap.parse_args()

    garments, persons = images_in(args.garments), images_in(args.persons)
    print(f"{len(garments)} garments × {len(persons)} persons = {len(garments) * len(persons)} runs")

    engine = load_engine()
    rows: list[str] = []
    for person in persons:
        cells: list[str] = [f"<th>{html.escape(person.name)}</th>"]
        for garment in garments:
            run_dir = args.out / f"{person.stem}__{garment.stem}"
            run_dir.mkdir(parents=True, exist_ok=True)
            t0 = time.monotonic()
            try:
                out = engine.run(
                    EngineInput(
                        person_image_path=str(person),
                        garment=GarmentAssets(front=str(garment)),
                        options={"cloth_type": args.cloth_type, "angles": [0]},
                    ),
                    run_dir,
                )
                view = out.views[0][1].relative_to(args.out)
                cells.append(
                    f'<td><img src="{view}" width="200"><br>'
                    f"{time.monotonic() - t0:.0f}s</td>")
                print(f"  ok  {person.stem} × {garment.stem} ({time.monotonic() - t0:.0f}s)")
            except Exception as e:  # noqa: BLE001 — 격자는 끝까지 돈다
                cells.append(f"<td>FAIL: {html.escape(str(e)[:120])}</td>")
                print(f"  FAIL {person.stem} × {garment.stem}: {e}")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    header = "".join(f"<th>{html.escape(g.name)}</th>" for g in garments)
    (args.out / "index.html").write_text(
        "<meta charset='utf-8'><style>td,th{border:1px solid #ccc;padding:4px;"
        "vertical-align:top;font:12px sans-serif}</style>"
        f"<table><tr><th></th>{header}</tr>{''.join(rows)}</table>",
        encoding="utf-8",
    )
    print(f"콘택트 시트 → {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
