start:
	docker compose down
	@kill -9 $$(lsof -t -i@127.0.0.1:8000) 2>/dev/null || true
	docker compose up --build

datadog-start:
	kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
	DD_LOGS_INJECTION=true \
	DD_SERVICE="project1" \
	DD_ENV="dev" \
	DD_VERSION="0.1.0" \
  	uv run ddtrace-run uvicorn backend.main:app --host 0.0.0.0 --port 8000
