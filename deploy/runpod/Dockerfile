# CatVTON 워커 컨테이너 (Step 2 컨테이너화 — GPU 프로바이더가 바뀌어도 재현).
# 빌드:  docker build -f deploy/runpod/Dockerfile -t trymeon-worker .
# 실행:  docker run --gpus all -p 8000:8000 -v trymeon-data:/data trymeon-worker
#
# detectron2 소스 빌드에 nvcc 가 필요해 devel 이미지를 쓴다.
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel

RUN apt-get update && apt-get install -y --no-install-recommends \
    git redis-server libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

ENV CATVTON_REPO=/opt/CatVTON
RUN git clone https://github.com/Zheng-Chong/CatVTON.git $CATVTON_REPO \
    && pip install --no-cache-dir -r $CATVTON_REPO/requirements.txt

COPY . /app
RUN pip install --no-cache-dir -e /app

ENV TRYON_ENGINE=catvton \
    QUEUE_MODE=redis \
    TRYMEON_DATA_DIR=/data \
    CORS_ORIGINS=*

WORKDIR /app
EXPOSE 8000
CMD ["bash", "-c", "redis-server --daemonize yes && rq worker tryon & uvicorn backend.app:app --host 0.0.0.0 --port 8000"]
