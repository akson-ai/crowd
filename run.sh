ALLOW_ORIGINS="http://localhost:5173" uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 0
