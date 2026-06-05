# app/routes/admin/dashboard.py

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.redis_client import redis_client
from app.deps import get_db, require_management
from app.models import User
from app.models.feedback import Feedback
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.models.valuation import ValuationReport
from app.schemas import (
    DashboardCountriesResponse,
    DashboardFeedbackResponse,
    DashboardOverviewResponse,
    DashboardSubscriptionBreakdownItem,
    DashboardUserRegistrationsResponse,
    DashboardUsersResponse,
    DashboardValuationsResponse,
)
from app.utils.logger_config import app_logger as logger
from app.utils.response import APIResponse, success_response

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["admin-dashboard"],
)

DASHBOARD_CACHE_PREFIX = "admin-dashboard"
DASHBOARD_CACHE_TTL_SECONDS = 60

OVERVIEW_EXAMPLE = {
    "success": True,
    "message": "Dashboard overview fetched successfully",
    "data": {
        "users": {
            "total": 184,
            "active": 176,
        },
        "subscriptions": {
            "total": 132,
            "active": 128,
        },
        "valuations": {
            "total": 945,
        },
    },
}

USERS_EXAMPLE = {
    "success": True,
    "message": "Users stats fetched successfully",
    "data": {
        "email_verified": 165,
        "email_unverified": 19,
        "inactive_users": 8,
        "new_users_last_30_days": 24,
    },
}

REGISTRATIONS_BY_YEAR_EXAMPLE = {
    "success": True,
    "message": "User registrations by year fetched successfully",
    "data": {
        "user_registrations_by_year": [
            {"year": 2022, "registrations": 18},
            {"year": 2023, "registrations": 31},
            {"year": 2024, "registrations": 42},
            {"year": 2025, "registrations": 57},
            {"year": 2026, "registrations": 24},
        ],
    },
}

SUBSCRIPTIONS_EXAMPLE = {
    "success": True,
    "message": "Subscriptions breakdown fetched successfully",
    "data": [
        {
            "country": "AE",
            "plan": "PRO",
            "currency": "AED",
            "price": 999,
            "subscriptions": {
                "total": 21,
                "active": 19,
            },
            "revenue": {
                "total": 20979,
                "active": 18981,
            },
        }
    ],
}

VALUATIONS_EXAMPLE = {
    "success": True,
    "message": "Valuations stats fetched successfully",
    "data": {
        "by_category": [
            {"category": "apartment", "count": 84},
            {"category": "villa", "count": 39},
            {"category": "warehouse", "count": 11},
        ],
        "last_30_days": 43,
    },
}

COUNTRIES_EXAMPLE = {
    "success": True,
    "message": "Country-wise stats fetched successfully",
    "data": {
        "subscriptions": [
            {"country": "AE", "count": 52},
            {"country": "IN", "count": 37},
        ],
        "valuations": [
            {"country": "AE", "count": 71},
            {"country": "IN", "count": 58},
        ],
    },
}

FEEDBACK_EXAMPLE = {
    "success": True,
    "message": "Feedback stats fetched successfully",
    "data": {
        "total_feedback": 94,
        "open_feedback": 7,
        "avg_rating": 4.37,
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dashboard_cache_key(name: str) -> str:
    return f"{DASHBOARD_CACHE_PREFIX}:{name}"


def _read_dashboard_cache(name: str) -> Any | None:
    try:
        cached_payload = redis_client.get(_dashboard_cache_key(name))
    except Exception:
        logger.warning("Dashboard cache read failed key=%s", name, exc_info=True)
        return None

    if not cached_payload:
        return None

    try:
        return json.loads(cached_payload)
    except json.JSONDecodeError:
        logger.warning("Dashboard cache payload invalid key=%s", name)
        return None


def _write_dashboard_cache(name: str, payload: Any) -> None:
    try:
        redis_client.setex(
            _dashboard_cache_key(name),
            DASHBOARD_CACHE_TTL_SECONDS,
            json.dumps(payload),
        )
    except Exception:
        logger.warning("Dashboard cache write failed key=%s", name, exc_info=True)


def _cached_dashboard_response(
    *,
    cache_name: str,
    success_message: str,
    builder: Callable[[], Any],
):
    cached_payload = _read_dashboard_cache(cache_name)
    if cached_payload is not None:
        logger.debug("Admin dashboard cache hit key=%s", cache_name)
        return success_response(
            data=cached_payload,
            message=success_message,
        )

    payload = builder()
    _write_dashboard_cache(cache_name, payload)
    return success_response(
        data=payload,
        message=success_message,
    )


@router.get(
    "/overview",
    response_model=APIResponse[DashboardOverviewResponse],
    summary="Get dashboard overview",
    description="Returns headline totals for users, subscriptions, and valuations.",
    responses={
        200: {
            "description": "Dashboard overview metrics.",
            "content": {
                "application/json": {
                    "example": OVERVIEW_EXAMPLE,
                }
            },
        }
    },
)
def dashboard_overview(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:
        logger.info("Admin dashboard: overview requested")

        def build_payload() -> dict:
            user_totals = db.query(
                func.count(User.id).label("total"),
                func.count(User.id).filter(User.is_active.is_(True)).label("active"),
            ).one()

            subscription_totals = db.query(
                func.count(UserSubscription.id).label("total"),
                func.count(UserSubscription.id)
                .filter(UserSubscription.is_active.is_(True))
                .label("active"),
            ).one()

            total_valuations = db.query(func.count(ValuationReport.id)).scalar() or 0

            logger.debug("Admin dashboard: overview aggregation completed")

            return {
                "users": {
                    "total": user_totals.total,
                    "active": user_totals.active,
                },
                "subscriptions": {
                    "total": subscription_totals.total,
                    "active": subscription_totals.active,
                },
                "valuations": {
                    "total": total_valuations,
                },
            }

        return _cached_dashboard_response(
            cache_name="overview",
            success_message="Dashboard overview fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard overview failed")
        raise HTTPException(500, "Failed to load dashboard overview")


@router.get(
    "/users",
    response_model=APIResponse[DashboardUsersResponse],
    summary="Get user dashboard stats",
    description="Returns email verification and recent-user metrics for the admin dashboard.",
    responses={
        200: {
            "description": "User metrics for the dashboard.",
            "content": {
                "application/json": {
                    "example": USERS_EXAMPLE,
                }
            },
        }
    },
)
def dashboard_users(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:
        logger.info("Admin dashboard: users stats requested")

        def build_payload() -> dict:
            last_30_days = _utc_now() - timedelta(days=30)
            stats = db.query(
                func.count(User.id)
                .filter(User.is_email_verified.is_(True))
                .label("verified"),
                func.count(User.id)
                .filter(User.is_email_verified.is_(False))
                .label("unverified"),
                func.count(User.id).filter(User.is_active.is_(False)).label("inactive"),
                func.count(User.id)
                .filter(User.email_verified_at >= last_30_days)
                .label("new_users_30d"),
            ).one()

            logger.debug("Admin dashboard: users stats aggregation completed")

            return {
                "email_verified": stats.verified,
                "email_unverified": stats.unverified,
                "inactive_users": stats.inactive,
                "new_users_last_30_days": stats.new_users_30d,
            }

        return _cached_dashboard_response(
            cache_name="users",
            success_message="Users stats fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard users stats failed")
        raise HTTPException(500, "Failed to load users stats")


@router.get(
    "/user-registrations-by-year",
    response_model=APIResponse[DashboardUserRegistrationsResponse],
    summary="Get yearly verified registrations",
    description="Returns verified user registrations grouped by year for the last five calendar years.",
    responses={
        200: {
            "description": "Five-year registration trend.",
            "content": {
                "application/json": {
                    "example": REGISTRATIONS_BY_YEAR_EXAMPLE,
                }
            },
        }
    },
)
def user_registrations_by_last_five_years(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:

        def build_payload() -> dict:
            current_year = _utc_now().year
            window_start = datetime(current_year - 4, 1, 1, tzinfo=timezone.utc)
            window_end = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
            registration_year = func.extract("year", User.email_verified_at)

            results = (
                db.query(
                    registration_year.label("year"),
                    func.count(User.id).label("total"),
                )
                .filter(
                    User.email_verified_at.isnot(None),
                    User.email_verified_at >= window_start,
                    User.email_verified_at < window_end,
                )
                .group_by(registration_year)
                .order_by(registration_year)
                .all()
            )

            year_data = {year: 0 for year in range(current_year - 4, current_year + 1)}

            for year, total in results:
                if year is not None:
                    year_data[int(year)] = total

            user_data_by_year = [
                {"year": year, "registrations": year_data[year]}
                for year in range(current_year - 4, current_year + 1)
            ]

            logger.debug(
                "Admin dashboard: user registrations by year aggregation completed"
            )

            return {"user_registrations_by_year": user_data_by_year}

        return _cached_dashboard_response(
            cache_name="user-registrations-by-year",
            success_message="User registrations by year fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Failed to load user registrations by year")
        raise HTTPException(500, "Failed to load user registrations by year")


@router.get(
    "/subscriptions",
    response_model=APIResponse[list[DashboardSubscriptionBreakdownItem]],
    summary="Get subscription breakdown",
    description=(
        "Returns subscription totals and derived revenue grouped by plan and plan country."
    ),
    responses={
        200: {
            "description": "Subscription and revenue breakdown.",
            "content": {
                "application/json": {
                    "example": SUBSCRIPTIONS_EXAMPLE,
                }
            },
        }
    },
)
def dashboard_subscriptions_country_wise(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:
        logger.info("Admin dashboard: subscriptions breakdown requested")

        def build_payload() -> list[dict]:
            rows = (
                db.query(
                    SubscriptionPlan.country_code,
                    SubscriptionPlan.name,
                    SubscriptionPlan.currency,
                    SubscriptionPlan.price,
                    func.count(UserSubscription.id).label("total"),
                    func.count(UserSubscription.id)
                    .filter(UserSubscription.is_active.is_(True))
                    .label("active"),
                )
                .outerjoin(
                    UserSubscription, SubscriptionPlan.id == UserSubscription.plan_id
                )
                .group_by(
                    SubscriptionPlan.country_code,
                    SubscriptionPlan.name,
                    SubscriptionPlan.currency,
                    SubscriptionPlan.price,
                )
                .order_by(
                    SubscriptionPlan.country_code,
                    SubscriptionPlan.name,
                )
                .all()
            )

            logger.debug("Admin dashboard: subscription aggregation completed")

            return [
                {
                    "country": row.country_code,
                    "plan": row.name,
                    "currency": row.currency,
                    "price": row.price,
                    "subscriptions": {
                        "total": row.total,
                        "active": row.active,
                    },
                    "revenue": {
                        "total": row.total * row.price,
                        "active": row.active * row.price,
                    },
                }
                for row in rows
            ]

        return _cached_dashboard_response(
            cache_name="subscriptions",
            success_message="Subscriptions breakdown fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard subscriptions breakdown failed")
        raise HTTPException(500, "Failed to load subscriptions breakdown")


@router.get(
    "/valuations",
    response_model=APIResponse[DashboardValuationsResponse],
    summary="Get valuation dashboard stats",
    description="Returns valuations grouped by category and a rolling 30-day total.",
    responses={
        200: {
            "description": "Valuation counts by category and recent activity.",
            "content": {
                "application/json": {
                    "example": VALUATIONS_EXAMPLE,
                }
            },
        }
    },
)
def dashboard_valuations(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:
        logger.info("Admin dashboard: valuation stats requested")

        def build_payload() -> dict:
            by_category = (
                db.query(
                    ValuationReport.category,
                    func.count(ValuationReport.id),
                )
                .group_by(ValuationReport.category)
                .order_by(ValuationReport.category)
                .all()
            )

            last_30_days = _utc_now() - timedelta(days=30)
            last_30d_count = (
                db.query(func.count(ValuationReport.id))
                .filter(ValuationReport.created_at >= last_30_days)
                .scalar()
                or 0
            )

            logger.debug("Admin dashboard: valuation aggregation completed")

            return {
                "by_category": [
                    {"category": category, "count": count}
                    for category, count in by_category
                ],
                "last_30_days": last_30d_count,
            }

        return _cached_dashboard_response(
            cache_name="valuations",
            success_message="Valuations stats fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard valuations stats failed")
        raise HTTPException(500, "Failed to load valuations stats")


@router.get(
    "/countries",
    response_model=APIResponse[DashboardCountriesResponse],
    summary="Get country-wise dashboard stats",
    description=(
        "Returns country-level counts for subscriptions and valuations shown on the admin dashboard."
    ),
    responses={
        200: {
            "description": "Country-wise subscription and valuation counts.",
            "content": {
                "application/json": {
                    "example": COUNTRIES_EXAMPLE,
                }
            },
        }
    },
)
def dashboard_countries(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:
        logger.info("Admin dashboard: country-wise stats requested")

        def build_payload() -> dict:
            subs_by_country = (
                db.query(
                    UserSubscription.pricing_country_code,
                    func.count(UserSubscription.id),
                )
                .group_by(UserSubscription.pricing_country_code)
                .order_by(UserSubscription.pricing_country_code)
                .all()
            )

            valuations_by_country = (
                db.query(
                    ValuationReport.country_code,
                    func.count(ValuationReport.id),
                )
                .group_by(ValuationReport.country_code)
                .order_by(ValuationReport.country_code)
                .all()
            )

            logger.debug("Admin dashboard: country-wise aggregation completed")

            return {
                "subscriptions": [
                    {"country": country, "count": count}
                    for country, count in subs_by_country
                ],
                "valuations": [
                    {"country": country, "count": count}
                    for country, count in valuations_by_country
                ],
            }

        return _cached_dashboard_response(
            cache_name="countries",
            success_message="Country-wise stats fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard country-wise stats failed")
        raise HTTPException(500, "Failed to load country-wise stats")


@router.get(
    "/feedback",
    response_model=APIResponse[DashboardFeedbackResponse],
    summary="Get feedback dashboard stats",
    description="Returns overall feedback volume, open feedback count, and average rating.",
    responses={
        200: {
            "description": "Feedback metrics for the admin dashboard.",
            "content": {
                "application/json": {
                    "example": FEEDBACK_EXAMPLE,
                }
            },
        }
    },
)
def feedback_stats(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    try:

        def build_payload() -> dict:
            stats = db.query(
                func.count(Feedback.id).label("total"),
                func.count(Feedback.id)
                .filter(Feedback.status == "OPEN")
                .label("open_count"),
                func.avg(Feedback.rating)
                .filter(Feedback.rating.isnot(None))
                .label("avg_rating"),
            ).one()

            return {
                "total_feedback": stats.total,
                "open_feedback": stats.open_count,
                "avg_rating": (
                    round(float(stats.avg_rating), 2)
                    if stats.avg_rating is not None
                    else None
                ),
            }

        return _cached_dashboard_response(
            cache_name="feedback",
            success_message="Feedback stats fetched successfully",
            builder=build_payload,
        )
    except Exception:
        logger.exception("Dashboard feedback stats failed")
        raise HTTPException(500, "Failed to load feedback stats")
