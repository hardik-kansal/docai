docker-start:
	docker compose up -d postgres redis minio qdrant

# i first installed postgres, redis on system level
# so when docker engine restarts system servies which are enable by default
# takes port, postgres have safety so it silently allows it,
# but redis fails to start saying port mapping failed
# disable them system level first for once

minio-hook:
	docker exec local_minio mc alias set local http://localhost:9000 hardik password
	docker exec local_minio mc event add local/contracts arn:minio:sqs::FASTAPI:webhook --event put -p
# mc is minio command tool, sqs is aws simple queue service	

# docker when do compose up, gets recent cached image
# if something in dockerfile changed, or in code
# needs to use --build to create a fresh new image 
# -d is detached, so will run in background rather in terminal 


#rm -rf /tmp/fastembed_cache/ use this when using a diff embedding model
celery-start:
	uv run celery -A backend.ingestion.worker.celery_app worker -E -Q ingestion -l info --concurrency=4

# -A is for application, 
# worker is just role
# -E enables to run in terminal, when task done can show
# -Q -> without it worker only listens and adds to redis, not process tasks
# -l info for logging to show
# --concurrency=4, creates 4 differnt seperate proccess, like 4 new applications

# lsof -t -i:8000 to get pids at 8000

start:
	@kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
	uv run fastapi dev backend/main.py

frontend-start:
	cd frontend && npm install && npm run dev

upload:
	 uv run python tests/upload_s3.py




	
