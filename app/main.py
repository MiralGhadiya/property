from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config_manager import load_config, start_listener_thread
from app.routes import auth as user_auth, valuation, subscription, payment, user_feedback, inquiry
from app.routes.admin import (
    auth,
    users,
    subscription_plans,
    user_subscriptions,
    valuations,
    dashboard,
    feedback,
    staff,
    inquiries,
    country,
    system_config,
)

import app.celery_app
from app.middleware.ip_country_middleware import IPCountryMiddleware
from app.middleware.ip_country import get_client_ip
from app.utils.logger_config import app_logger as logger


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

app.add_middleware(IPCountryMiddleware)

@app.middleware("http")
async def add_ngrok_header(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Routers (User)
# --------------------------------------------------

app.include_router(user_auth.router)
app.include_router(valuation.router)
app.include_router(subscription.router)
app.include_router(payment.router)
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
    response: Response = await call_next(request)

    if request.url.path != "/health":
        logger.debug(
            "Request IP resolved ip=%s country=%s",
            get_client_ip(request),
            getattr(request.state, "ip_country", None),
        )

    return response
