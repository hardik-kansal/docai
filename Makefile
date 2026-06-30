docker-start:
	docker compose down
	@kill -9 $$(lsof -t -i@127.0.0.1:8000) 2>/dev/null || true
	docker compose up -d postgres redis migrate minio
	
# docker when do compose up, gets recent cached image
# if something in dockerfile changed, or in code
# needs to use --build to create a fresh new image  


# datadog-start:
# 	kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
# 	DD_LOGS_INJECTION=true \
# 	DD_SERVICE="project1" \
# 	DD_ENV="dev" \
# 	DD_VERSION="0.1.0" \
#   	uv run ddtrace-run uvicorn backend.main:app --host 0.0.0.0 --port 8000

celery-start:
	uv run celery -A backend.ingestion.worker.celery_app worker -E -Q ingestion -l info --concurrency=4

# -A is for application, worker is just role, uses 4 cores max if can
# means 4 differnt files can be processed at a time.
# -E enables task to monitor in terminal
# -Q without it worker only listens and adds to redis, not process tasks

start:
	@kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
	uv run fastapi dev backend/main.py

minio-start:
	docker exec local_minio mc alias set local http://localhost:9000 hardik password
	docker exec local_minio mc event add local/contracts arn:minio:sqs::FASTAPI:webhook --event put -p


	
