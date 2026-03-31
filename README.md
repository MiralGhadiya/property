# Desktop Valuation Platform

Desktop Valuation is a FastAPI application for generating property valuations, managing subscriptions, handling payments, and running admin operations. The project uses PostgreSQL for persistence, Redis plus Celery for background jobs, and Docker Compose for full-stack deployment.

## Core Features

- User registration, login, email verification, and password flows
- AI-assisted property valuation generation
- PDF valuation report generation
- Subscription plans and country-aware pricing
- Razorpay payment integration
- Admin endpoints for users, staff, valuations, subscriptions, inquiries, feedback, countries, and system configuration
- Background jobs for valuations, subscription expiry, reminders, and exchange-rate updates

## Tech Stack

- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL
- Redis
- Celery
- OpenAI and Gemini integrations
- Nginx + Docker Compose

## Prerequisites

- Python 3.10+ recommended
- PostgreSQL
- Redis
- A populated `.env` file

For Docker deployment on a Linux server, you only need:

- Docker
- Docker Compose plugin (`docker compose`)
- A populated `.env` file

## Environment Configuration

Copy `.env.example` to `.env` and fill in the required values.

Use standard `KEY=value` formatting in `.env` with no spaces around `=`, because Docker Compose env files are stricter than Python dotenv parsing.

The app supports two database configuration styles:

1. Set `DATABASE_URL`
2. Leave `DATABASE_URL` empty and use `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`

Important variables:

- `ENV`
- `DATABASE_URL` or the full `POSTGRES_*` set
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `EMAIL_USER`
- `EMAIL_PASSWORD`
- `ADMIN_FEEDBACK_EMAILS`
- `BASE_URL`
- `FRONTEND_URL`
- `IPINFO_TOKEN`
- `EXCHANGE_RATE_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_CLIENT_ID`

If you want Docker Compose to use the bundled `postgres` service, leave `DATABASE_URL` empty or commented out. Otherwise the app will keep connecting to the external database URL from `.env`.

`POSTGRES_SSLMODE`, `POSTGRES_CONNECT_TIMEOUT`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and `DB_POOL_RECYCLE` are also supported for production-style database connections.

## Local Development Setup

1. Create and activate a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create your environment file.

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

4. Make sure PostgreSQL and Redis are running and that `.env` points to them.

5. Run database migrations.

```bash
alembic upgrade head
```

6. Run the initial project bootstrap script.

```bash
python -m app.scripts.setup_project
```

This script:

- imports values from `.env` into the `system_config` table
- then imports countries from `data - data.csv.csv`
- then creates default subscription settings
- then seeds these management users into the `users` table if they do not already exist:
- `superadmin@gmail.com` / `superadmin` / `SUPER_ADMIN`
- `admin@gmail.com` / `admin` / `ADMIN`
- and finally imports subscription plans from `subscription_plans.xlsx`

Each bootstrap step is committed before the next one starts, so country-dependent inserts run only after country data is already stored. If matching data already exists, the script skips it safely instead of inserting duplicates.

7. Start the API server.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

8. Start Celery worker and beat in separate terminals.

```bash
celery -A app.celery_app worker -l info
```

```bash
celery -A app.celery_app beat -l info
```

## Local URLs

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Compose Setup

The repository includes services for:

- `postgres`
- `redis`
- `api`
- `celery_worker`
- `celery_beat`
- `nginx`

This Compose stack is prepared for Linux server deployment:

- only Nginx is exposed publicly by default
- PostgreSQL and Redis stay on the internal Docker network
- database, Redis data, uploads, generated reports, Celery beat state, and app logs are persisted in Docker volumes
- the API waits for PostgreSQL and Redis before starting
- the API runs Alembic migrations automatically on startup
- the API runs the project bootstrap automatically on startup after migrations

Start everything with:

```bash
docker compose up -d --build
```

Check service status with:

```bash
docker compose ps
```

Follow logs with:

```bash
docker compose logs -f api
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

The API container now bootstraps the project automatically during startup. It imports config values, then countries, then subscription settings, then seeds the two management users, and finally imports subscription plans from `subscription_plans.xlsx` without duplicating existing data.

Useful URLs with the default Compose setup:

- App via Nginx: `http://localhost`
- Swagger UI via Nginx: `http://localhost/docs`

Notes about the container startup flow:

- `start.sh` is shared by the API, Celery worker, and Celery beat containers
- `start.sh` waits for PostgreSQL and Redis before starting the process
- the API container runs `alembic upgrade head` before launching Uvicorn
- Compose defaults `POSTGRES_HOST` to `postgres` and `REDIS_URL` to `redis://redis:6379/0`
- Nginx listens on `NGINX_PORT` from `.env` and defaults to `80`
- PM2 is not required for this deployment mode because Docker Compose already manages the running services

## Linux Server Deployment

1. Install Docker and the Docker Compose plugin on the server.
2. Copy the project to the server.
3. Create `.env` from `.env.example`.
4. If you want to use the PostgreSQL container from this project, comment out or empty `DATABASE_URL`.
5. Set at least these values in `.env`:

- `ENV=production`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `REDIS_URL=redis://redis:6379/0`
- `BASE_URL`
- `FRONTEND_URL`
- `JWT_SECRET_KEY`

6. Build and start the stack:

```bash
docker compose up -d --build
```

7. Let the API container finish its automatic bootstrap after startup.

8. If your server has a firewall, allow the Nginx port you configured, usually `80`.

To stop the stack:

```bash
docker compose down
```

To stop it and also remove the persisted Docker volumes:

```bash
docker compose down -v
```

## Common Management Commands

Create a superuser only:

```bash
python -m app.scripts.create_superuser
```

Import `.env` values into the database only:

```bash
python -m app.scripts.import_env_to_db
```

## Project Documents

- `PROJECT_SETUP_INSTRUCTIONS.md`
- `API_DOCUMENTATION.md`
- `PROJECT_ARCHITECTURE.md`
- `FLOW_DOCUMENTATION.md`
- `PROJECT_FLOW_DOCUMENTATION.md`

## Notes

- Database schema is migration-first: run `alembic upgrade head` before app bootstrap scripts if you are not using Docker startup.
- `docker-compose.yml`, `Dockerfile`, and `start.sh` are aligned around the Docker workflow described above.
