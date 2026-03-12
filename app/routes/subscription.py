#app/routes/subscription.py

from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from app.services.country_service import get_country_by_country_code

from app.models import User
from app.models.subscription import SubscriptionPlan, UserSubscription

from app.services.exchange_rate_service import get_rate
from app.services.currency_resolver import resolve_currency

from app.common import PaginatedResponse
from app.routes.payment import create_order

from app.utils.date_filters import filter_by_date_range
from app.utils.logger_config import app_logger as logger

from app.deps import get_db, get_current_user, get_current_user_optional, pagination_params


router = APIRouter(prefix="/subscription", tags=["subscription"])
    
@router.get("/plans")
def list_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    
    ip_country = getattr(request.state, "ip_country", None)
    
    if current_user and current_user.country:
        user_country = current_user.country.country_code
        print("user_country", user_country)
    else:
        user_country = None
        
    print(user_country)

    country = ip_country or user_country or "DEFAULT"

    logger.info(
        f"IP country={ip_country}, "
        f"user country={current_user.country.country_code if current_user and current_user.country else None}, "
        f"final pricing country={country}"
    )
    
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == country,
        SubscriptionPlan.is_active == True,
    ).all()

    if plans:
        return plans

    usd_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.country_code == "DEFAULT",
        SubscriptionPlan.currency == "USD",
        SubscriptionPlan.is_active == True,
    ).all()

    if not usd_plans:
        return []
    
    # country_obj = get_country_by_country_code(db, country)

    # if country_obj and country_obj.currency_code:
    #     user_currency = country_obj.currency_code
    # else:
    #     user_currency = "USD"
    
    
    # Try to resolve currency from user profile first
    profile_currency = (
        current_user.country.currency_code
        if current_user and current_user.country and current_user.country.currency_code
        else None
    )

    user_currency = "USD"
    rate = None

    # Step 2: Use profile currency if valid
    profile_currency = (
        current_user.country.currency_code
        if current_user and current_user.country and current_user.country.currency_code
        else None
    )

    user_currency, rate = resolve_currency(
        db=db,
        country_code=country,
        profile_currency=profile_currency
    )

    if rate is None:
        logger.warning(f"No exchange rate for currency={user_currency}")
    # rate = get_rate(db, user_currency) if user_currency != "USD" else None
    
    if rate is None:
        logger.warning(f"No exchange rate for currency={user_currency}")

    response = []
    for plan in usd_plans:
        # converted_price = round(plan.price * rate, 2) if rate else plan.price
        converted_price = (
            round(plan.price * rate, 2)
            if rate is not None
            else plan.price
        )

        response.append({
            "id": plan.id,
            "name": plan.name,
            "price": converted_price,
            "currency": user_currency if rate else "USD",
            "converted": True,
            "base_price_usd": plan.price,
        })

    return response


@router.get("/my-plans")
def get_my_active_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    try:
        plans = (
            db.query(UserSubscription)
            .join(SubscriptionPlan)
            .filter(
                UserSubscription.user_id == current_user.id,
                UserSubscription.is_active == True,
                UserSubscription.start_date <= now,
                UserSubscription.end_date >= now,
                SubscriptionPlan.is_active == True,
            )
            .order_by(UserSubscription.end_date.asc())
            .all()
        )
    except Exception:
        logger.exception("Failed to fetch user subscriptions")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve subscriptions"
        )

    return [
        {
            "subscription_id": s.id,
            "plan_name": s.plan.name,
            "country": s.plan.country_code,
            "price": s.plan.price,
            "currency": s.plan.currency,
            "max_reports": s.plan.max_reports,
            "reports_used": s.reports_used,
            "remaining": (
                None if s.plan.max_reports is None
                else s.plan.max_reports - s.reports_used
            ),
            "start_date": s.start_date,
            "end_date": s.end_date,
        }
        for s in plans
    ]
    
    
@router.get(
    "/plan-history",
    response_model=PaginatedResponse[dict]
)
def subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),

    params: dict = Depends(pagination_params),
    is_active: Optional[bool] = Query(None),
    
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    logger.info(
        f"Fetching subscription history user_id={current_user.id} "
        f"page={params['page']} limit={params['limit']}"
    )

    query = (
        db.query(UserSubscription)
        .join(SubscriptionPlan)
        .filter(UserSubscription.user_id == current_user.id)
    )

    if params["search"]:
        query = query.filter(
            SubscriptionPlan.name.ilike(
                f"%{params['search']}%"
            )
        )

    if is_active is not None:
        query = query.filter(
            UserSubscription.is_active == is_active
        )
        
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
    for s in subs:
        end_date = s.end_date
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        data.append({
            "subscription_id": s.id,
            "plan_name": s.plan.name,
            "country": s.plan.country_code,
            "price": s.plan.price,
            "currency": s.plan.currency,
            "max_reports": s.plan.max_reports,
            "reports_used": s.reports_used,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "is_active": s.is_active,
            "expired": end_date < now if end_date else False,
            "purchased_on": s.start_date,
        })

    return {
        "data": data,
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        }
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
            .order_by(
                SubscriptionPlan.price.desc(),
                UserSubscription.end_date.desc()
            )
            .first()
        )
    except Exception:
        logger.exception("Failed to fetch default subscription")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve default subscription"
        )

    if not sub:
        raise HTTPException(404, "No active subscription")

    return {
        "subscription_id": sub.id,
        "plan": sub.plan.name,
        "remaining": (
            None if sub.plan.max_reports is None
            else sub.plan.max_reports - sub.reports_used
        ),
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
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    now = datetime.now(timezone.utc)

    end_date = subscription.end_date
    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    max_reports = subscription.plan.max_reports
    reports_used = subscription.reports_used

    remaining = (
        None
        if max_reports is None
        else max(0, max_reports - reports_used)
    )

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
    sub = db.query(UserSubscription).filter(
        UserSubscription.id == subscription_id,
        UserSubscription.user_id == current_user.id,
        UserSubscription.is_active == True,
    ).first()

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
    sub = db.query(UserSubscription).filter(
        UserSubscription.id == subscription_id,
        UserSubscription.user_id == current_user.id,
    ).first()

    if not sub:
        raise HTTPException(404, "Subscription not found")

    return create_order(sub.plan_id, request, db, current_user)
