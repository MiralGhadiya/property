import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import importlib
importlib.import_module("app.celery_app")
from app.core.config_manager import load_config, start_listener_thread
from app.middleware.ip_country import get_client_ip
from app.middleware.ip_country_middleware import IPCountryMiddleware
from app.routes import auth as user_auth
from app.routes import (
    inquiry,
    payment,
    subscription,
    unified_payment,
    user_feedback,
    valuation,
)
from app.routes.admin import (
    auth,
    country,
    dashboard,
    feedback,
    inquiries,
    staff,
    subscription_plans,
    system_config,
    user_subscriptions,
    users,
    valuations,
)
from app.utils.logger_config import app_logger as logger
from app.utils.logger_config import shutdown_logging

logger.info("Starting Desktop Valuation API")

app = FastAPI(title="Desktop Valuation API")


@app.get("/health", tags=["system"])
def healthcheck():
    return {"status": "ok"}


@app.on_event("startup")
def startup_event():
    logger.info("Loading system configuration from database...")
    load_config()
    # auto_reload(10)
    start_listener_thread()
    logger.info("System configuration loaded")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down Desktop Valuation API")
    shutdown_logging()


@app.middleware("http")
async def add_ngrok_header(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


# ✅ ADD CORS HERE (top)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://desktopvaluation.in",
        "https://www.desktopvaluation.in",
        "https://admin.desktopvaluation.in",
        # "http://localhost:5173",
        # "http://127.0.0.1:5173",
        # "http://localhost:3000",
        # "http://127.0.0.1:3000",
        # "http://192.168.1.71:5173",
        # "https://penholder-splicing-audacity.ngrok-free.dev",
        # "*",
    ],
    # allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(IPCountryMiddleware)

# --------------------------------------------------
# Routers (User)
# --------------------------------------------------

app.include_router(user_auth.router)
app.include_router(valuation.router)
app.include_router(subscription.router)
app.include_router(payment.router)
app.include_router(unified_payment.router)
app.include_router(user_feedback.router)
app.include_router(inquiry.router)

# --------------------------------------------------
# Routers (Admin)
# --------------------------------------------------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(subscription_plans.router)
app.include_router(user_subscriptions.router)
app.include_router(valuations.router)
app.include_router(dashboard.router)
app.include_router(feedback.router)
app.include_router(staff.router)
app.include_router(inquiries.router)
app.include_router(country.router)
app.include_router(system_config.router)

# --------------------------------------------------
# IP → Country middleware
# --------------------------------------------------


@app.middleware("http")
async def log_ip_country_resolution(request: Request, call_next):
    start_time = time.perf_counter()
    client_ip = get_client_ip(request)

    try:
        response: Response = await call_next(request)
    except Exception:
        logger.exception(
            "HTTP request failed method=%s path=%s ip=%s country=%s",
            request.method,
            request.url.path,
            client_ip,
            getattr(request.state, "ip_country", None),
        )
        raise

    is_internal_healthcheck = request.url.path == "/health" and client_ip in {
        "127.0.0.1",
        "::1",
    }

    if not is_internal_healthcheck:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "HTTP request method=%s path=%s status_code=%s duration_ms=%.2f ip=%s country=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
            getattr(request.state, "ip_country", None),
        )

    return response
