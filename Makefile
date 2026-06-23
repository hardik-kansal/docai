start:
	kill -9 $$(lsof -t -i:8000) 2>/dev/null || true
	uv run fastapi dev backend/main.py