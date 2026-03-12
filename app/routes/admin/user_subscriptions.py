#app/routes/admin/user_subscriptions.py

from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_db, require_management, require_superuser, pagination_params

from app.models import User
from app.models.subscription import SubscriptionPlan, UserSubscription

from app.models.subscription_settings import SubscriptionSettings
from app.schemas import UpdateSubscription, UserSubscriptionResponse, AssignSubscription

from app.common import PaginatedResponse
from app.schemas.admin import UpdateSubscriptionDuration
from app.utils.date_filters import filter_by_date_range
from app.utils.response import APIResponse, success_response

from app.utils.logger_config import app_logger as logger

router = APIRouter(
    prefix="/admin",
    tags=["admin-user-subscriptions"]
)

class UserSubscriptionFilters:
    def __init__(
        self,
        user_id: Optional[int] = Query(None),
        plan_id: Optional[int] = Query(None),
        is_active: Optional[bool] = Query(None),
        is_expired: Optional[bool] = Query(None),
        payment_status: Optional[str] = Query(None),
        pricing_country_code: Optional[str] = Query(None),
        ip_country_code: Optional[str] = Query(None),
        payment_country_code: Optional[str] = Query(None),
        plan_country_code: Optional[str] = Query(None),
        start_from: Optional[datetime] = Query(None),
        start_to: Optional[datetime] = Query(None),
        end_from: Optional[datetime] = Query(None),
        end_to: Optional[datetime] = Query(None),
        purchased_within_days: Optional[int] = Query(None, ge=1, le=365),
    ):
        self.user_id = user_id
        self.plan_id = plan_id
        self.is_active = is_active
        self.is_expired = is_expired
        self.payment_status = payment_status

        self.pricing_country_code = pricing_country_code
        self.ip_country_code = ip_country_code
        self.payment_country_code = payment_country_code
        self.plan_country_code = plan_country_code

        self.start_from = start_from
        self.start_to = start_to
        self.end_from = end_from
        self.end_to = end_to
        self.purchased_within_days = purchased_within_days


@router.get("/user-subscriptions", response_model=APIResponse[PaginatedResponse[UserSubscriptionResponse]])
def list_all_user_subscriptions(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    params: dict = Depends(pagination_params),
    filters: UserSubscriptionFilters = Depends(),
    
):
    logger.info(
        "Admin listing user subscriptions "
        f"user_id={filters.user_id} plan_id={filters.plan_id} is_active={filters.is_active} "
        f"search={params['search']}"
    )
        
    if filters.start_from and filters.start_to and filters.start_from > filters.start_to:
        raise HTTPException(400, "Invalid date range")
    
    query = (
        db.query(UserSubscription)
        .join(SubscriptionPlan)
    )

    if params["search"]:
        query = query.filter(
            SubscriptionPlan.name.ilike(f"%{params['search']}%")
        )

    if filters.user_id:
        query = query.filter(UserSubscription.user_id == filters.user_id)

    if filters.plan_id:
        query = query.filter(UserSubscription.plan_id == filters.plan_id)

    if filters.is_active is not None:
        query = query.filter(UserSubscription.is_active == filters.is_active)

    if filters.is_expired is not None:
        query = query.filter(UserSubscription.is_expired == filters.is_expired)

    if filters.payment_status:
        query = query.filter(
            UserSubscription.payment_status == filters.payment_status.upper()
        )

    if filters.pricing_country_code:
        query = query.filter(
            UserSubscription.pricing_country_code ==
            filters.pricing_country_code.upper()
        )

    if filters.ip_country_code:
        query = query.filter(
            UserSubscription.ip_country_code ==
            filters.ip_country_code.upper()
        )

    if filters.payment_country_code:
        query = query.filter(
            UserSubscription.payment_country_code ==
            filters.payment_country_code.upper()
        )

    if filters.plan_country_code:
        query = query.filter(
            SubscriptionPlan.country_code ==
            filters.plan_country_code.upper()
        )

    query = filter_by_date_range(
        query,
        UserSubscription.start_date,
        filters.start_from,
        filters.start_to,
    )

    query = filter_by_date_range(
        query,
        UserSubscription.end_date,
        filters.end_from,
        filters.end_to,
    )

    if filters.purchased_within_days:
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(
            days=filters.purchased_within_days
        )
        query = query.filter(
            UserSubscription.start_date >= start_date
        )
        
    total = query.count()

    if params["limit"] is not None:
        subs = (
            query
            .order_by(UserSubscription.start_date.desc())
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        subs = query.order_by(UserSubscription.start_date.desc()).all()
    
    logger.debug(f"Admin fetched user subscriptions count={len(subs)}")

    return success_response(
        data={
            "data": [
                UserSubscriptionResponse(
                    id=s.id,
                    user_id=s.user_id,
                    plan_id=s.plan_id,
                    plan_name=s.plan.name,
                    pricing_country_code=s.pricing_country_code,
                    start_date=s.start_date,
                    end_date=s.end_date,
                    reports_used=s.reports_used,
                    is_active=s.is_active,
                )
            for s in subs
        ],
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        },
    },
        message="User subscriptions fetched successfully"
    )
    

@router.get("/users/{user_id}/subscriptions", response_model=APIResponse[PaginatedResponse[UserSubscriptionResponse]])
def get_user_subscriptions(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    
    params: dict = Depends(pagination_params),
    payment_status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    country_code: Optional[str] = Query(None),
    start_from: Optional[datetime] = Query(None),
    start_to: Optional[datetime] = Query(None),

):
    logger.info(
        f"Admin fetching subscriptions for user_id={user_id} "
        f"search={params['search']}"
    )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User not found while fetching subscriptions user_id={user_id}")
        raise HTTPException(404, "User not found")
    
    if start_from and start_to and start_from > start_to:
        raise HTTPException(400, "Invalid date range")
        
    query = (
        db.query(UserSubscription)
        .join(SubscriptionPlan)
        .filter(UserSubscription.user_id == user_id)
    )

    if params["search"]:
        query = query.filter(
            SubscriptionPlan.name.ilike(f"%{params['search']}%")
        )

    if payment_status:
        query = query.filter(
            UserSubscription.payment_status == payment_status.upper()
        )

    if is_active is not None:
        query = query.filter(
            UserSubscription.is_active == is_active
        )

    if country_code:
        query = query.filter(
            UserSubscription.pricing_country_code == country_code.upper()
        )

    if start_from:
        query = query.filter(
            UserSubscription.start_date >= start_from
        )

    if start_to:
        query = query.filter(
            UserSubscription.start_date <= start_to
        )
    
    total = query.count()

    if params["limit"] is not None:
        subs = (
            query
            .order_by(UserSubscription.start_date.desc())
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        subs = query.order_by(UserSubscription.start_date.desc()).all()
    
    logger.debug(
        f"Admin fetched subscriptions for user_id={user_id} count={len(subs)}"
    )

    return success_response(
        data={
            "data": [
                UserSubscriptionResponse(
                    id=s.id,
                    user_id=s.user_id,
                    plan_id=s.plan_id,
                    plan_name=s.plan.name,
                    pricing_country_code=s.pricing_country_code,
                    start_date=s.start_date,
                    end_date=s.end_date,
                    reports_used=s.reports_used,
                    is_active=s.is_active,
            )
            for s in subs
        ],
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        }
    },
        message="User subscriptions fetched successfully"
    )


@router.post("/users/{user_id}/assign-subscription", response_model=APIResponse[UserSubscriptionResponse])
def assign_subscription_to_user(
    user_id: UUID,
    data: AssignSubscription,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(
        f"Admin assigning subscription user_id={user_id} "
        f"plan_id={data.plan_id} duration_days={data.duration_days}"
    )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User not found while assigning subscription user_id={user_id}")
        raise HTTPException(404, "User not found")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == data.plan_id,
        SubscriptionPlan.is_active == True
    ).first()

    if not plan:
        logger.warning(
            f"Subscription plan not found while assigning plan_id={data.plan_id}"
        )
        raise HTTPException(404, "Subscription plan not found")

    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=data.duration_days)

    sub = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        pricing_country_code=data.pricing_country_code or plan.country_code,
        ip_country_code=None,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )
    try:
        db.add(sub)
        db.commit()
        db.refresh(sub)
    except Exception:
        db.rollback()
        logger.exception("Failed to assign subscription to user")
        raise HTTPException(500, "Subscription assignment failed")
    
    logger.info(
        f"Subscription assigned sub_id={sub.id} "
        f"user_id={user.id} plan_id={plan.id}"
    )

    return success_response(
        data=UserSubscriptionResponse(
            id=sub.id,
            user_id=sub.user_id,
            plan_id=sub.plan_id,
            plan_name=plan.name,
            pricing_country_code=sub.pricing_country_code,
            start_date=sub.start_date,
            end_date=sub.end_date,
            reports_used=sub.reports_used,
            is_active=sub.is_active,
        ),
        message="Subscription assigned successfully"
    )


@router.patch("/user-subscriptions/{subscription_id}", response_model=APIResponse[dict])
def update_user_subscription(
    subscription_id: UUID,
    data: UpdateSubscription,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin updating subscription sub_id={subscription_id}")

    sub = db.query(UserSubscription).filter(
        UserSubscription.id == subscription_id
    ).first()
    
    if not sub:
        raise HTTPException(404, "Subscription not found")
    
    try:
        changes = []

        if data.extend_days:
            sub.end_date += timedelta(days=data.extend_days)
            changes.append(f"extend_days={data.extend_days}")

        if data.reset_reports_used:
            sub.reports_used = 0
            changes.append("reset_reports_used")

        if data.deactivate:
            sub.is_active = False
            changes.append("deactivated")

        db.commit()
        
    except Exception:
        db.rollback()
        logger.exception("Failed to update user subscription")
        raise HTTPException(500, "Update failed")

    logger.info(
        f"Subscription updated sub_id={subscription_id} "
        f"changes={changes}"
    )

    return success_response(
        data={},
        message="Subscription updated successfully"
    )


@router.post("/user-subscriptions/{subscription_id}/cancel", response_model=APIResponse[dict])
def cancel_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin cancelling subscription sub_id={subscription_id}")

    sub = db.query(UserSubscription).filter(
        UserSubscription.id == subscription_id
    ).first()

    if not sub:
        logger.warning(f"Subscription not found during cancel sub_id={subscription_id}")
        raise HTTPException(404, "Subscription not found")
    
    try:
        sub.is_active = False
        sub.end_date = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to cancel subscription")
        raise HTTPException(500, "Cancel failed")
    
    logger.info(f"Subscription cancelled sub_id={subscription_id}")

    return success_response(
        data={},
        message="Subscription cancelled successfully"
    )
    
    
@router.patch("/subscription-duration")
def update_subscription_duration(
    data: UpdateSubscriptionDuration,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    if data.duration_days <= 0:
        raise HTTPException(400, "Duration must be greater than 0")

    settings = db.query(SubscriptionSettings).first()

    if not settings:
        settings = SubscriptionSettings(
            subscription_duration_days=data.duration_days
        )
        db.add(settings)
    else:
        settings.subscription_duration_days = data.duration_days

    db.commit()

    return {
        "message": "Subscription duration updated successfully",
        "new_duration_days": data.duration_days
    }