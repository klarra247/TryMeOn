#!/usr/bin/env bash
# GPU pod 에서 Redis + API + CatVTON 워커를 한 번에 기동 (Phase 1 토폴로지).
# 프론트(맥)는 VITE_API_TARGET 으로 이 pod 의 8000 포트 공개 URL을 가리킨다.
set -euo pipefail

TRYMEON_REPO=${TRYMEON_REPO:-/workspace/TryMeOn}
export CATVTON_REPO=${CATVTON_REPO:-/workspace/CatVTON}
export TRYON_ENGINE=${TRYON_ENGINE:-catvton}
export QUEUE_MODE=redis
export TRYMEON_DATA_DIR=${TRYMEON_DATA_DIR:-/workspace/data}
# RunPod 프록시 오리진은 가변적이라 개발 중엔 열어둔다 (파일럿 전 잠글 것)
export CORS_ORIGINS=${CORS_ORIGINS:-*}

cd "$TRYMEON_REPO"

redis-server --daemonize yes

echo "== RQ 워커 (engine=$TRYON_ENGINE) =="
rq worker tryon > /workspace/worker.log 2>&1 &

echo "== API :8000 =="
exec uvicorn backend.app:app --host 0.0.0.0 --port 8000
