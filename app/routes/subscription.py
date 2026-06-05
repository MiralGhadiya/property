# app/routes/subscription.py

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.common import PaginatedResponse
from app.deps import get_current_user, get_current_user_optional, get_db, pagination_params
from app.models import User
from app.models.country import Country
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.routes.payment import create_order
from app.services.pricing import get_plans_with_pricing
from app.utils.date_filters import filter_by_date_range
from app.utils.logger_config import app_logger as logger
from app.utils.maps import geocode_address

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/plans")
def list_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    ip_country = getattr(request.state, "ip_country", None)

    user_country = current_user.country.country_code if current_user and current_user.country else None

    country = ip_country or user_country or "DEFAULT"

    return get_plans_with_pricing(db, country, current_user)


@router.get("/plans/by-address")
def get_plans_by_address_get(
    address: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    geo = geocode_address(address)

    if not geo:
        raise HTTPException(400, "Unable to detect location")

    country = geo.get("country_code") or "DEFAULT"

    return get_plans_with_pricing(db, country, current_user, force_currency_by_country=True)


@router.get("/my-plans")
def get_my_active_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    try:
        plans = (
            db.query(
                UserSubscription.id,
                UserSubscription.reports_used,
                UserSubscription.start_date,
                UserSubscription.end_date,
                SubscriptionPlan.name.label("plan_name"),
                SubscriptionPlan.country_code,
                SubscriptionPlan.price,
                SubscriptionPlan.currency,
                SubscriptionPlan.max_reports,
                Country.name.label("country_name"),
            )
            .join(SubscriptionPlan)
            .outerjoin(Country, Country.country_code == SubscriptionPlan.country_code)
            .filter(
                UserSubscription.user_id == current_user.id,
                UserSubscription.is_active == True,
                UserSubscription.start_date <= now,
                UserSubscription.end_date >= now,
                SubscriptionPlan.is_active == True,
            )
            .filter(
                (SubscriptionPlan.max_reports == None) | (UserSubscription.reports_used < SubscriptionPlan.max_reports)
            )
            .order_by(UserSubscription.end_date.asc())
            .all()
        )
    except Exception:
        logger.exception("Failed to fetch user subscriptions")
        raise HTTPException(status_code=500, detail="Could not retrieve subscriptions")

    return [
        {
            "subscription_id": subscription.id,
            "plan_name": subscription.plan_name,
            "country": subscription.country_code,
            "country_name": ("Global" if subscription.country_code == "GLOBAL" else subscription.country_name),
            "price": subscription.price,
            "currency": subscription.currency,
            "max_reports": subscription.max_reports,
            "reports_used": subscription.reports_used,
            "remaining": (
                None
                if subscription.max_reports is None
                else max(0, subscription.max_reports - subscription.reports_used)
            ),
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
        }
        for subscription in plans
    ]


@router.get("/plan-history", response_model=PaginatedResponse[dict])
def subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    params: dict = Depends(pagination_params),
    is_active: Optional[bool] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    logger.info(
        f"Fetching subscription history user_id={current_user.id} " f"page={params['page']} limit={params['limit']}"
    )

    query = (
        db.query(
            UserSubscription.id,
            UserSubscription.reports_used,
            UserSubscription.start_date,
            UserSubscription.end_date,
            UserSubscription.is_active,
            SubscriptionPlan.name.label("plan_name"),
            SubscriptionPlan.country_code,
            SubscriptionPlan.price,
            SubscriptionPlan.currency,
            SubscriptionPlan.max_reports,
        )
        .join(SubscriptionPlan)
        .filter(UserSubscription.user_id == current_user.id)
    )

    if params["search"]:
        query = query.filter(SubscriptionPlan.name.ilike(f"%{params['search']}%"))

    if is_active is not None:
        query = query.filter(UserSubscription.is_active == is_active)

    query = filter_by_date_range(
        query,
        UserSubscription.start_date,
        from_date,
        to_date,
    )

    total = query.count()

    query = query.order_by(UserSubscription.start_date.desc())
    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"])

    subs = query.all()

    now = datetime.now(timezone.utc)

    data = []
    for subscription in subs:
        end_date = subscription.end_date
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        data.append(
            {
                "subscription_id": subscription.id,
                "plan_name": subscription.plan_name,
                "country": subscription.country_code,
                "price": subscription.price,
                "currency": subscription.currency,
                "max_reports": subscription.max_reports,
                "reports_used": subscription.reports_used,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "is_active": subscription.is_active,
                "expired": end_date < now if end_date else False,
                "purchased_on": subscription.start_date,
            }
        )

    return {
        "data": data,
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        },
    }


@router.get("/default")
def get_default_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    try:
        sub = (
            db.query(UserSubscription)
            .join(SubscriptionPlan)
            .filter(
                UserSubscription.user_id == current_user.id,
                UserSubscription.is_active == True,
                UserSubscription.start_date <= now,
                UserSubscription.end_date >= now,
            )
            .order_by(SubscriptionPlan.price.desc(), UserSubscription.end_date.desc())
            .first()
        )
    except Exception:
        logger.exception("Failed to fetch default subscription")
        raise HTTPException(status_code=500, detail="Could not retrieve default subscription")

    if not sub:
        raise HTTPException(404, "No active subscription")

    return {
        "subscription_id": sub.id,
        "plan": sub.plan.name,
        "remaining": (None if sub.plan.max_reports is None else max(0, sub.plan.max_reports - sub.reports_used)),
    }


@router.get("/{subscription_id}/usage")
def get_subscription_usage(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = (
        db.query(UserSubscription)
        .join(SubscriptionPlan)
        .filter(
            UserSubscription.id == subscription_id,
            UserSubscription.user_id == current_user.id,
        )
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    now = datetime.now(timezone.utc)

    end_date = subscription.end_date
    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    max_reports = subscription.plan.max_reports
    reports_used = subscription.reports_used

    remaining = None if max_reports is None else max(0, max_reports - reports_used)

    return {
        "subscription_id": subscription.id,
        "plan_name": subscription.plan.name,
        "max_reports": max_reports,
        "reports_used": reports_used,
        "remaining": remaining,
        "expires_at": end_date,
        "is_active": subscription.is_active and end_date >= now,
    }


@router.post("/{subscription_id}/cancel")
def cancel_my_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.id == subscription_id,
            UserSubscription.user_id == current_user.id,
            UserSubscription.is_active == True,
        )
        .first()
    )

    if not sub:
        raise HTTPException(404, "Active subscription not found")

    sub.auto_renew = False
    sub.cancelled_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Subscription will cancel at period end",
        "ends_on": sub.end_date,
    }


@router.post("/{subscription_id}/renew")
def renew_subscription(
    subscription_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.id == subscription_id,
            UserSubscription.user_id == current_user.id,
        )
        .first()
    )

    if not sub:
        raise HTTPException(404, "Subscription not found")

    return create_order(sub.plan_id, request, db, current_user)
