#!/bin/sh
set -e

cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PYTHON="venv/bin/python"
else
  PYTHON="python"
fi

echo "Running migrations..."
"$PYTHON" -m alembic upgrade head

echo "Running project setup bootstrap..."
"$PYTHON" -m app.scripts.setup_project

echo "Starting FastAPI..."
exec "$PYTHON" -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips="*"

