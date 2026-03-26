# syntax=docker/dockerfile:1.7
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY alembic ./alembic
COPY app ./app
COPY alembic.ini ./
COPY start.sh ./
COPY ["data - data.csv.csv", "./data - data.csv.csv"]

RUN mkdir -p /app/generated_reports /app/uploads /app/app/logs /app/run \
    && chmod +x /app/start.sh

EXPOSE 8000

CMD ["./start.sh", "api"]
