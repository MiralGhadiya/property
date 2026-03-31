# Project Setup Instructions

This document is the detailed setup and deployment guide for the Desktop Valuation project.

The recommended production approach for this project is:

- Docker Compose
- One service per container
- Nginx as the public entry point
- PostgreSQL and Redis managed by Docker unless you intentionally use external services

PM2 is not required for this deployment flow.

## 1. Recommended Deployment Architecture

This project is already structured for Docker-based deployment through [docker-compose.yml](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/docker-compose.yml).

The default Compose stack includes:

- `postgres`
- `redis`
- `api`
- `celery_worker`
- `celery_beat`
- `nginx`

What each service does:

- `postgres`: application database
- `redis`: Celery broker/backend and config cache support
- `api`: FastAPI application
- `celery_worker`: background task processor
- `celery_beat`: scheduled task runner
- `nginx`: reverse proxy exposed publicly

## 2. Important Files

These files are the main deployment-related files in this project:

- [docker-compose.yml](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/docker-compose.yml)
- [Dockerfile](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/Dockerfile)
- [start.sh](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/start.sh)
- [.env.example](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/.env.example)
- [nginx/nginx.conf](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/nginx/nginx.conf)
- [README.md](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/README.md)

## 3. How Container Startup Works

The shared startup script is [start.sh](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/start.sh).

Its behavior is:

- wait for PostgreSQL
- wait for Redis
- run Alembic migrations automatically for the `api` service
- run project bootstrap automatically for the `api` service
- start the API, Celery worker, or Celery beat depending on container command

This means:

- you do not need PM2
- you do not need to manually start Uvicorn inside the container
- you do not need to manually run migrations on every deployment

The API container now completes bootstrap automatically after migrations during startup.

## 4. Server Requirements

Recommended minimum production setup:

- Linux server
- Docker installed
- Docker Compose plugin installed
- open port `80` on the firewall
- a populated `.env` file

For Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

After adding your user to the `docker` group, log out and log back in once.

Verify installation:

```bash
docker --version
docker compose version
```

## 5. Copy the Project to the Server

Example using `git`:

```bash
cd /opt
sudo git clone <your-repo-url> desktop_valuation-miral
sudo chown -R $USER:$USER /opt/desktop_valuation-miral
cd /opt/desktop_valuation-miral
```

If you are not using git on the server, upload the project directory manually and then `cd` into it.

## 6. Create the Production Environment File

Start from the example file:

```bash
cp .env.example .env
nano .env
```

Use standard `KEY=value` format with no spaces around `=`.

## 7. Production `.env` Example for Full Docker Setup

Use the following pattern when you want Docker Compose to run PostgreSQL and Redis too.

```env
ENV=production

# Leave empty when using the postgres container from docker-compose.yml
DATABASE_URL=

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=desktop_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-strong-password

POSTGRES_SSLMODE=prefer
POSTGRES_CONNECT_TIMEOUT=10

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800

REDIS_URL=redis://redis:6379/0
NGINX_PORT=80

BASE_URL=http://YOUR_SERVER_IP_OR_DOMAIN
FRONTEND_URL=http://YOUR_FRONTEND_DOMAIN

JWT_SECRET_KEY=put-a-long-random-secret-here
ALGORITHM=HS256

EMAIL_USER=your-email@example.com
EMAIL_PASSWORD=your-email-password
ADMIN_FEEDBACK_EMAILS=admin@example.com

OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
IPINFO_TOKEN=your-ipinfo-token
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret
EXCHANGE_RATE_API_KEY=your-exchange-rate-key
GOOGLE_MAPS_API_KEY=your-google-maps-key
GOOGLE_CLIENT_ID=your-google-client-id

STARTUP_MAX_RETRIES=20
STARTUP_RETRY_DELAY=3
```

Important notes:

- keep `DATABASE_URL` empty if you want to use the Docker `postgres` service
- keep `POSTGRES_HOST=postgres` when using the Docker `postgres` service
- keep `REDIS_URL=redis://redis:6379/0` when using the Docker `redis` service
- set `BASE_URL` to your public backend URL or server IP
- set `FRONTEND_URL` to your frontend URL
- use a strong value for `JWT_SECRET_KEY`

## 8. If You Want to Use External PostgreSQL Instead

If your database is hosted outside Docker, set `DATABASE_URL` and do not rely on `POSTGRES_HOST=postgres`.

Example:

```env
DATABASE_URL=postgresql+psycopg2://username:password@your-db-host:5432/desktop_db
REDIS_URL=redis://redis:6379/0
```

In that case:

- `DATABASE_URL` becomes the main database setting
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are not needed for app connection logic

## 9. First Deployment

From the project root on the server, run:

```bash
docker compose up -d --build
```

This will:

- build the Python image
- install Python dependencies
- install Playwright Chromium inside the image
- start PostgreSQL, Redis, API, worker, beat, and Nginx

Check container status:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f api
docker compose logs -f celery_worker
docker compose logs -f celery_beat
docker compose logs -f nginx
```

## 10. Automatic Bootstrap

After the stack is up, the `api` container runs the bootstrap automatically.

That bootstrap will:

- import `.env` values into the `system_config` table
- then import countries from `data - data.csv.csv`
- then create default subscription settings
- then seed these management users into the `users` table if they do not already exist:
- `superadmin@gmail.com` with username `superadmin`, role `SUPER_ADMIN`, and password `superadmin`
- `admin@gmail.com` with username `admin`, role `ADMIN`, and password `admin`
- and finally import subscription plans from `subscription_plans.xlsx`

Each bootstrap step is committed before the next one starts, so country-dependent rows are created only after countries are already stored. If data already exists, the bootstrap skips it safely instead of inserting duplicates.

If you want to rerun the bootstrap manually:

```bash
docker compose exec api python -m app.scripts.setup_project
```

If you only need to create a superuser later:

```bash
docker compose exec api python -m app.scripts.create_superuser
```

If you only need to import `.env` values later:

```bash
docker compose exec api python -m app.scripts.import_env_to_db
```

## 11. Access the Application

If `NGINX_PORT=80`, your app should be available at:

- `http://YOUR_SERVER_IP_OR_DOMAIN`
- `http://YOUR_SERVER_IP_OR_DOMAIN/docs`

The default Nginx config used by Docker is [nginx/nginx.conf](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/nginx/nginx.conf).

## 12. Daily Operations

Start the stack:

```bash
docker compose up -d
```

Stop the stack:

```bash
docker compose down
```

Stop and remove volumes too:

```bash
docker compose down -v
```

Restart everything:

```bash
docker compose restart
```

Restart only one service:

```bash
docker compose restart api
docker compose restart celery_worker
docker compose restart celery_beat
docker compose restart nginx
```

View running services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
```

Open a shell inside the API container:

```bash
docker compose exec api sh
```

## 13. Deploy Code Updates Later

When you update the code on the server:

```bash
git pull
docker compose up -d --build
```

Because the API service runs migrations automatically during container startup, schema updates should apply when the refreshed API container starts.

After deployment, verify:

- `docker compose ps`
- `docker compose logs -f api`
- `docker compose logs -f celery_worker`
- `docker compose logs -f celery_beat`

## 14. Data Persistence

The Docker Compose setup already persists important data using volumes:

- PostgreSQL data
- Redis data
- generated reports
- uploads
- application logs
- Celery beat schedule data

These are defined in [docker-compose.yml](C:/Users/evenm/Downloads/desktop_valuation-miral/desktop_valuation-miral/docker-compose.yml).

Because of this:

- rebuilding containers does not delete your database
- rebuilding containers does not delete uploads or generated reports
- `docker compose down` is safe for normal stops
- `docker compose down -v` is destructive because it removes volumes

## 15. Firewall and Networking

At minimum, allow the port you expose through Nginx.

If `NGINX_PORT=80`, allow:

- TCP `80`

Example for Ubuntu with UFW:

```bash
sudo ufw allow 80/tcp
sudo ufw enable
sudo ufw status
```

PostgreSQL and Redis are not exposed publicly by default in the included Compose setup, which is good for security.

## 16. Domain and SSL Recommendation

For initial testing, using the server IP is fine.

For real production:

1. point a domain to the server
2. configure HTTPS/SSL
3. change `BASE_URL` to the real backend domain
4. change `FRONTEND_URL` to the real frontend domain

Recommended next step after basic deployment is working:

- add SSL with Nginx and Let's Encrypt

## 17. Troubleshooting

If `api` keeps restarting:

- check `docker compose logs -f api`
- verify `.env` values
- verify DB and Redis settings
- verify required API keys and secrets are set

If database connection fails:

- if using Docker PostgreSQL, keep `DATABASE_URL=` empty
- if using Docker PostgreSQL, keep `POSTGRES_HOST=postgres`
- verify `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`

If Redis connection fails:

- verify `REDIS_URL=redis://redis:6379/0` for internal Docker networking
- check `docker compose logs -f redis`

If Nginx is not reachable:

- check `docker compose ps`
- check `docker compose logs -f nginx`
- verify firewall allows the configured public port

If automatic bootstrap fails:

- make sure the containers are already up
- confirm migrations completed successfully in API logs
- rerun:

```bash
docker compose exec api python -m app.scripts.setup_project
```

## 18. Recommended Production Workflow Summary

For this project, the recommended production workflow is:

1. Install Docker and Docker Compose on the Linux server
2. Copy the project to the server
3. Create `.env`
4. Run `docker compose up -d --build`
5. Let the API container finish automatic bootstrap
6. Verify the app at `/docs`
7. Add domain and SSL later

## 19. Quick Command Reference

Initial deployment:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
docker compose logs -f celery_worker
docker compose logs -f celery_beat
docker compose logs -f nginx
```

Restart services:

```bash
docker compose restart
```

Update deployment:

```bash
git pull
docker compose up -d --build
```

Stop services:

```bash
docker compose down
```
