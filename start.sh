#!/bin/sh
set -e

service_name="${1:-api}"
max_retries="${STARTUP_MAX_RETRIES:-20}"
retry_delay="${STARTUP_RETRY_DELAY:-3}"

wait_for_database() {
  python - <<'PY'
from sqlalchemy import text
from app.database.db import engine

with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
PY
}

wait_for_redis() {
  python - <<'PY'
from app.core.redis_client import redis_client

redis_client.ping()
PY
}

wait_with_retries() {
  dependency_name="$1"
  check_function="$2"
  attempt=1

  until "$check_function"; do
    if [ "$attempt" -ge "$max_retries" ]; then
      echo "$dependency_name did not become ready after $attempt attempts."
      exit 1
    fi

    echo "Waiting for $dependency_name. Retrying in ${retry_delay}s..."
    attempt=$((attempt + 1))
    sleep "$retry_delay"
  done
}

run_migrations() {
  attempt=1

  echo "Running migrations..."

  until python -m app.scripts.run_migrations; do
    if [ "$attempt" -ge "$max_retries" ]; then
      echo "Database migrations failed after $attempt attempts."
      exit 1
    fi

    echo "Migration step failed. Retrying in ${retry_delay}s..."
    attempt=$((attempt + 1))
    sleep "$retry_delay"
  done
}

run_project_setup() {
  attempt=1

  echo "Running project setup bootstrap..."

  until python -m app.scripts.setup_project; do
    if [ "$attempt" -ge "$max_retries" ]; then
      echo "Project setup bootstrap failed after $attempt attempts."
      exit 1
    fi

    echo "Project setup bootstrap failed. Retrying in ${retry_delay}s..."
    attempt=$((attempt + 1))
    sleep "$retry_delay"
  done
}

wait_with_retries "PostgreSQL" "wait_for_database"
wait_with_retries "Redis" "wait_for_redis"

case "$service_name" in
  api)
    run_migrations
    run_project_setup
    echo "Starting FastAPI..."
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --proxy-headers \
      --forwarded-allow-ips="*"
    ;;
  worker)
    echo "Starting Celery worker..."
    exec celery -A app.celery_app worker -l info
    ;;
  beat)
    echo "Starting Celery beat..."
    exec celery -A app.celery_app beat -l info --schedule run/celerybeat-schedule
    ;;
  *)
    echo "Unknown service: $service_name"
    echo "Use one of: api, worker, beat"
    exit 1
    ;;
esac
