# Phase 1 — RunPod 실행 가이드

> ⚠️ CatVTON 은 CC BY-NC-SA (비상업). 학습·프로토타입 용도로만 (docs/LICENSES.md).

## Step 1 — GPU 확보 & 모델 단독 실행 (hello world)

1. RunPod → **RTX 4090** pod, 템플릿 **RunPod PyTorch 2.x (CUDA 12)**,
   볼륨 `/workspace` 50GB+, HTTP 포트 **8000, 7860** 노출.
2. pod 터미널에서:
   ```bash
   cd /workspace
   git clone <이 repo URL> TryMeOn
   bash TryMeOn/deploy/runpod/setup_pod.sh
   ```
3. **앱과 완전히 분리해서** CatVTON 자체 Gradio 로 착용 이미지 1장 뽑기:
   ```bash
   cd /workspace/CatVTON && python app.py
   ```
   → `https://<pod-id>-7860.proxy.runpod.net` 접속, 샘플 사람/의류로 생성.
   **여기서 "모델이 실제로 돈다"가 증명되기 전에는 아래로 내려가지 말 것.**
   결과 품질 감도 이 단계에서 잡는다 (스크린샷 저장 → docs/FAILURE_MODES.md).

   ※ setup 스크립트는 python 3.10+ 단일 환경을 먼저 시도한다. detectron2/
   densepose 설치가 실패하면 공식 README 대로 conda python 3.9 분리 환경을
   만들고, 그 환경에 `pip install -e /workspace/TryMeOn` 이 안 되면(3.9 는
   우리 코드 미지원) 워커만 3.10+ 환경에서 돌리는 구성으로 조정한다.

## Step 2~5 — 앱 연결

1. 스톡 모델 사진 배치 (마네킹 모드용, 딱 한 번):
   ```bash
   mkdir -p /workspace/data/models/mannequin-default
   # 정면 전신 사진 1장을 person.png 로 복사 (VITON-HD 테스트 이미지 등)
   ```
2. 전체 기동:
   ```bash
   bash /workspace/TryMeOn/deploy/runpod/start_all.sh
   ```
   Redis + RQ 워커(catvton 엔진) + API :8000 이 pod 안에서 함께 돈다.
3. 스모크 (pod 터미널):
   ```bash
   curl -s localhost:8000/api/products | head -c 300
   curl -s -X POST localhost:8000/api/tryon -F product_id=tshirt-coral -F mode=mannequin
   curl -s localhost:8000/api/tryon/<job_id>   # done 까지 폴링, 첫 실행은 모델 로드로 수 분
   ```
4. 맥에서 키오스크 연결:
   ```bash
   VITE_API_TARGET=https://<pod-id>-8000.proxy.runpod.net npm run dev
   ```
   → 상품 선택 → **진짜 CatVTON 착용샷**이 뷰어에 뜨면 Phase 1 루프 완성.
   backend/frontend 코드 0줄 변경으로 됐는지 확인 (엔진 격리 원칙 검증).
5. 마네킹 사전 캐싱: `curl -X POST localhost:8000/api/products/<id>/prewarm`
   → 두 번째 조회부터 `meta.cache_hit=true`, 키오스크 대기 0초.

## Step 6 — 실패 모드 관찰

```bash
python /workspace/TryMeOn/experiments/batch_tryon.py \
  --garments /workspace/data/test/garments --persons /workspace/data/test/persons
```
→ `experiments/out/batch/` 에 격자 결과 + `index.html` 콘택트 시트.
관찰 기록은 `docs/FAILURE_MODES.md` 에.

## 비용 메모

- 4090 시간당 ~$0.4-0.7 (community). **쓰고 나면 pod stop** — 볼륨만 유지하면
  체크포인트 재다운로드 없이 재개된다.
- bf16 1024×768 생성 ≈ 8GB VRAM. 4090(24GB)이면 Step 7 IDM-VTON(SDXL)도 가능.

## 검증 상태

이 디렉터리의 스크립트와 `worker/engine/catvton.py`, `worker/preprocessing/
schp_densepose.py` 는 **GPU 없는 환경에서 작성돼 실행 검증 전**이다.
CatVTON repo 의 공개 소스(app.py, cloth_masker.py)에서 확인한 시그니처
기준으로 작성했고, Step 1 헬로월드 후 Step 3 연결 시점에 실검증한다.
