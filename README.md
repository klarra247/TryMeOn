# TryMeOn — 버추얼 트라이온 키오스크 SaaS

매장 키오스크에서 손님이 옷을 (마네킹 또는 본인 사진으로) 입어보고,
좌우로 돌려가며 다면을 확인하는 B2B SaaS.
전체 그림은 **[docs/DESIGN.md](docs/DESIGN.md)** (단일 진실 출처) 참고.

> ⚠️ CatVTON/IDM-VTON 은 **비상업 라이선스** — 학습·프로토타입 전용.
> 상세: [docs/LICENSES.md](docs/LICENSES.md)

## 현재 상태: Phase 1 — 이미지 VTON 실작동 (코드 완성, GPU 검증 대기)

```
키오스크(React, 맥) ──▶ GPU pod 공개 URL
                          ├─ FastAPI :8000 (+/media)
                          ├─ Redis + RQ 워커
                          └─ TryOnEngine ├─ dummy   (GPU 불필요, 로컬 개발용)
                                         └─ catvton (SCHP+DensePose 마스크 → CatVTON 추론)
```

- 엔진 선택: `TRYON_ENGINE=dummy|catvton` — backend/frontend 코드는 동일.
- 마네킹 모드: (model, garment) 키 결과 캐싱 + `POST /api/products/{id}/prewarm`
  으로 등록 시점 사전 생성 → 키오스크 대기 0초.
- **RunPod 실행 절차: [deploy/runpod/README.md](deploy/runpod/README.md)**
  (CatVTON 연동 코드는 GPU 환경에서 최종 검증 전)

## 구조

```
shared/     계약의 단일 진실 출처 — schemas.py(canonical) + types.ts(미러)
backend/    FastAPI: 카탈로그, 트라이온 enqueue/폴링, 미디어 서빙, SQLite 잡 스토어
worker/     TryOnEngine 인터페이스 + 더미 엔진 + 전처리 모듈 인터페이스
frontend/   키오스크 UI: 상품 목록 → 마네킹/촬영 → N앵글 스와이퍼 뷰어
experiments/ 학습 스크립트 (SD1.5 inpaint 1회 실행 — CatVTON 베이스 이해용)
docs/       설계 문서, 라이선스 메모
```

## 시작하기 (맥)

사전 준비: [Homebrew](https://brew.sh) → `brew install uv node`,
[Docker Desktop](https://docker.com) (Redis 용).

```bash
make setup          # uv sync + npm install
make test           # e2e 테스트 (Redis 불필요)

# 전체 데모 — 터미널 4개:
make redis          # ① Redis (Docker)
make api            # ② FastAPI :8000
make worker         # ③ RQ 워커 (더미 엔진)
make front          # ④ 키오스크 :5173

# 또는 Redis/워커 없이 간단히 (thread 큐 모드):
make demo           # ①' API+워커 한 프로세스 :8000
make front          # ②' 키오스크 :5173
```

http://localhost:5173 → 상품 선택 → 더미 착용 결과가 3앵글(-45°/0°/+45°)로
뜨고 화살표/스와이프로 넘어가면 **Phase 0 완료 기준 달성**.

MPS 확인(선택): `uv run python -c "import torch; print(torch.backends.mps.is_available())"`
(torch 는 `uv sync --extra learn` 후에)

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/products` | 상품 목록 |
| GET | `/api/products/{id}` | 상품 상세 |
| POST | `/api/tryon` | 트라이온 enqueue (multipart: `product_id`, `mode`, `person_image?`) |
| GET | `/api/tryon/{id}` | 폴링 → `TryOnResult` 미디어 번들 |
| GET | `/media/*` | 이미지 정적 서빙 |

## 핵심 계약 (여길 바꾸면 신중히)

- `shared/schemas.py` — `TryOnResult` 미디어 번들 (`views[] + clip? + asset3d?`),
  `EngineInput`, `PreprocessArtifacts`. TS 미러는 `shared/types.ts`.
- `worker/engine/base.py` — `TryOnEngine` ABC. Phase 1의 CatVTON 은 구현체 하나로 추가.
- `worker/preprocessing/base.py` — 전처리(=cloth-agnostic 마스크 생성) 인터페이스.
  무거운 구현(SCHP+DensePose)은 Phase 1 클라우드 GPU 컨테이너 몫.

## Phase 0 학습 과제 (코드 밖)

- [ ] `experiments/sd_inpaint_smoke.py` 를 맥에서 실행 (`uv sync --extra learn`)
- [ ] CatVTON repo README + 논문(arXiv 2407.15886) 정독 — "concatenation" 발상 이해
- [ ] `Zheng-Chong/Awesome-Try-On-Models` 훑기
