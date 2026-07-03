"""Phase 0 완료 기준 검증: 상품 선택 → (더미) 미디어 번들이 뷰어 규격으로 돌아온다.

QUEUE_MODE=sync 로 요청 안에서 워커까지 동기 실행 — Redis 불필요.
"""
import io
import os
import tempfile

os.environ["QUEUE_MODE"] = "sync"
os.environ["TRYMEON_DATA_DIR"] = tempfile.mkdtemp(prefix="trymeon-test-")

import worker.engine.dummy as dummy_engine

dummy_engine.SIMULATED_LATENCY_SEC = 0  # 테스트에선 지연 생략

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import app


def _client() -> TestClient:
    return TestClient(app)


def test_catalog_seeded():
    with _client() as c:
        products = c.get("/api/products").json()
        assert len(products) >= 3
        assert all(p["garment"]["front"].startswith("/media/") for p in products)
        # 데이터 과수집 원칙: 뒷면 슬롯도 시드부터 채움
        assert all(p["garment"]["back"] for p in products)


def test_mannequin_tryon_returns_bundle():
    with _client() as c:
        pid = c.get("/api/products").json()[0]["id"]
        job = c.post("/api/tryon", data={"product_id": pid, "mode": "mannequin"}).json()

        result = c.get(f"/api/tryon/{job['id']}").json()
        assert result["status"] == "done"
        assert result["schema_version"] == 1
        assert len(result["views"]) == 3
        angles = [v["angle"] for v in result["views"]]
        assert angles == [-45, 0, 45]
        # 뷰 이미지가 실제로 서빙되는지
        for v in result["views"]:
            assert c.get(v["url"]).status_code == 200
        # 미래 슬롯이 스키마에 존재
        assert "clip" in result and "asset3d" in result


def test_user_tryon_with_photo():
    buf = io.BytesIO()
    Image.new("RGB", (720, 1280), (90, 120, 150)).save(buf, format="PNG")
    buf.seek(0)

    with _client() as c:
        pid = c.get("/api/products").json()[0]["id"]
        job = c.post(
            "/api/tryon",
            data={"product_id": pid, "mode": "user"},
            files={"person_image": ("person.png", buf, "image/png")},
        ).json()
        result = c.get(f"/api/tryon/{job['id']}").json()
        assert result["status"] == "done"
        assert result["mode"] == "user"
        assert len(result["views"]) == 3


def test_mannequin_result_is_cached():
    """Step 5: (model, garment) 캐시 — 두 번째 요청은 엔진을 안 거친다."""
    with _client() as c:
        pid = c.get("/api/products").json()[1]["id"]
        first = c.post("/api/tryon", data={"product_id": pid, "mode": "mannequin"}).json()
        r1 = c.get(f"/api/tryon/{first['id']}").json()
        assert r1["status"] == "done" and r1["meta"]["cache_hit"] is False

        second = c.post("/api/tryon", data={"product_id": pid, "mode": "mannequin"}).json()
        r2 = c.get(f"/api/tryon/{second['id']}").json()
        assert r2["status"] == "done" and r2["meta"]["cache_hit"] is True
        assert [v["url"] for v in r2["views"]] == [v["url"] for v in r1["views"]]


def test_prewarm_endpoint():
    """온보딩 훅: 등록 시점 사전 캐싱 → 키오스크 대기 0초."""
    with _client() as c:
        pid = c.get("/api/products").json()[2]["id"]
        warm = c.post(f"/api/products/{pid}/prewarm").json()
        assert c.get(f"/api/tryon/{warm['id']}").json()["status"] == "done"

        job = c.post("/api/tryon", data={"product_id": pid, "mode": "mannequin"}).json()
        assert c.get(f"/api/tryon/{job['id']}").json()["meta"]["cache_hit"] is True


def test_cloth_type_mapping():
    from shared.schemas import GarmentAssets, Product
    from worker.tasks import cloth_type_for

    def prod(tags):
        return Product(id="x", name="x", price=0,
                       garment=GarmentAssets(front="/media/x.png"), tags=tags)

    assert cloth_type_for(prod(["상의", "캐주얼"])) == "upper"
    assert cloth_type_for(prod(["원피스"])) == "overall"
    assert cloth_type_for(prod(["하의"])) == "lower"
    assert cloth_type_for(prod(["기타"])) == "upper"  # 기본값


def test_user_mode_requires_photo():
    with _client() as c:
        pid = c.get("/api/products").json()[0]["id"]
        res = c.post("/api/tryon", data={"product_id": pid, "mode": "user"})
        assert res.status_code == 422
