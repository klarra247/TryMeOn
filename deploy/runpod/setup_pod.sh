#!/usr/bin/env bash
# RunPod GPU pod 초기 세팅 (Step 1~4).
# 전제: RunPod PyTorch 템플릿 (CUDA 12.x, /workspace 볼륨), RTX 4090.
# 사용: bash deploy/runpod/setup_pod.sh
set -euo pipefail

WORKSPACE=${WORKSPACE:-/workspace}
CATVTON_REPO=${CATVTON_REPO:-$WORKSPACE/CatVTON}
TRYMEON_REPO=${TRYMEON_REPO:-$WORKSPACE/TryMeOn}

echo "== 1. 시스템 패키지 =="
apt-get update -qq
apt-get install -y -qq redis-server git

echo "== 2. CatVTON clone + 의존성 =="
# 공식 README 는 python 3.9 conda 를 권장하지만, 우리 워커 코드(3.11)와
# 한 환경을 쓰기 위해 3.10+ 에 먼저 시도한다. detectron2 빌드가 실패하면
# 그때 conda 3.9 분리 환경으로 폴백 (deploy/runpod/README.md 참고).
if [ ! -d "$CATVTON_REPO" ]; then
  git clone https://github.com/Zheng-Chong/CatVTON.git "$CATVTON_REPO"
fi
pip install -q -r "$CATVTON_REPO/requirements.txt"

echo "== 3. TryMeOn 워커/백엔드 설치 =="
pip install -q -e "$TRYMEON_REPO"

echo "== 4. 체크포인트 프리페치 (HF 자동 다운로드, ~수 GB) =="
python - <<'EOF'
from huggingface_hub import snapshot_download
p = snapshot_download(repo_id="zhengchong/CatVTON")
print("CatVTON ckpt:", p)
EOF

echo "== 완료 =="
echo "다음: Step 1 헬로월드 →  cd $CATVTON_REPO && python app.py  (Gradio :7860)"
echo "그 후: bash $TRYMEON_REPO/deploy/runpod/start_all.sh"
