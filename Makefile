# TryMeOn 개발 명령 모음. 전체 데모 = redis + api + worker + front (터미널 4개)
.PHONY: setup redis api worker front test demo

setup:            ## Python(uv) + 프론트(npm) 의존성 설치
	uv sync --extra dev
	cd frontend && npm install

redis:            ## 작업 큐용 Redis (Docker)
	docker compose up redis

api:              ## FastAPI 서버 :8000
	uv run uvicorn backend.app:app --reload --port 8000

worker:           ## RQ 워커 (더미 엔진)
	uv run rq worker tryon

front:            ## 키오스크 프론트 :5173
	cd frontend && npm run dev

test:             ## 백엔드 e2e 테스트 (Redis 불필요)
	uv run pytest -v

demo:             ## Redis 없이 한 프로세스로 데모 (thread 큐 모드)
	QUEUE_MODE=thread uv run uvicorn backend.app:app --port 8000
