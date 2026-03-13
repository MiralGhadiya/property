#app/routes/admin/subscription_plans.py

from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from app.deps import get_db, require_management
from app.models.subscription import SubscriptionPlan
from app.schemas import SubscriptionPlanResponse, SubscriptionPlanCreate, SubscriptionPlanUpdate
from app.services.subscription_service import add_subscription_plans_from_excel

from app.deps import pagination_params
from app.common import PaginatedResponse

from app.utils.response import APIResponse, success_response
from app.utils.date_filters import filter_by_date_range

from app.utils.logger_config import app_logger as logger

router = APIRouter(
    prefix="/admin/subscription-plans",
    tags=["admin-subscription-plans"]
)

SUBSCRIPTION_PLAN_NOT_FOUND = "Subscription plan not found"


class SubscriptionPlanFilters:
    def __init__(
        self,
        country_code: Optional[str] = Query(None),
        is_active: Optional[bool] = Query(None),

        min_price: Optional[int] = Query(None, ge=0),
        max_price: Optional[int] = Query(None, ge=0),
        
        max_reports: Optional[int] = Query(None, ge=0),
        min_reports: Optional[int] = Query(None, ge=0),

        currency: Optional[str] = Query(None),

        created_from: Optional[datetime] = Query(None),
        created_to: Optional[datetime] = Query(None),

        category: Optional[str] = Query(None),
    ):
        self.country_code = country_code
        self.is_active = is_active
        self.min_price = min_price
        self.max_price = max_price
        self.min_reports = min_reports
        self.max_reports = max_reports
        self.currency = currency
        self.created_from = created_from
        self.created_to = created_to
        self.category = category
        

@router.get("", response_model=APIResponse[PaginatedResponse[SubscriptionPlanResponse]])
def list_subscription_plans(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    
    params: dict = Depends(pagination_params),
    
    filters: SubscriptionPlanFilters = Depends(),

):
    logger.info(
        "Admin subscription plans list requested "
        f"country_code={filters.country_code} is_active={filters.is_active} "
        f"search={params['search']}"
    )

    query = db.query(SubscriptionPlan)

    if params["search"]:
        query = query.filter(
            SubscriptionPlan.name.ilike(f"%{params['search']}%")
        )

    if filters.country_code:
        query = query.filter(
            SubscriptionPlan.country_code == filters.country_code.upper()
        )

    if filters.is_active is not None:
        query = query.filter(
            SubscriptionPlan.is_active == filters.is_active
        )

    if filters.min_price is not None:
        query = query.filter(SubscriptionPlan.price >= filters.min_price)

    if filters.max_price is not None:
        query = query.filter(SubscriptionPlan.price <= filters.max_price)

    if filters.currency:
        query = query.filter(
            SubscriptionPlan.currency == filters.currency.upper()
        )

    if filters.min_reports is not None:
        query = query.filter(
            SubscriptionPlan.max_reports >= filters.min_reports
        )

    if filters.max_reports is not None:
        query = query.filter(
            SubscriptionPlan.max_reports <= filters.max_reports
        )

    if filters.category:
        query = query.filter(
            SubscriptionPlan.allowed_categories.contains(
                [filters.category]
            )
        )
        
    query = filter_by_date_range(
        query,
        SubscriptionPlan.created_at,
        filters.created_from,
        filters.created_to,
    )

    total = query.count()

    query = query.order_by(SubscriptionPlan.country_code.asc())
    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"])
    
    plans = query.all()

    logger.debug(f"Admin subscription plans fetched count={len(plans)}")

    return success_response(
        data={
            "data": plans,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
        }
    },
        message="Subscription plans fetched"
    )
    
    
@router.get("/{plan_id}", response_model=APIResponse[SubscriptionPlanResponse])
def get_subscription_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin requested subscription plan plan_id={plan_id}")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id
    ).first()

    if not plan:
        logger.warning(f"{SUBSCRIPTION_PLAN_NOT_FOUND} plan_id={plan_id}")
        raise HTTPException(404, SUBSCRIPTION_PLAN_NOT_FOUND)

    return success_response(data=plan, message="Subscription plan fetched")


@router.post("", response_model=APIResponse[SubscriptionPlanResponse])
def create_subscription_plan(
    data: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(
        "Admin creating subscription plan "
        f"name={data.name} country={data.country_code}"
    )

    plan = SubscriptionPlan(
        name=data.name.upper(),
        country_code=data.country_code.upper(),
        price=data.price,
        currency=data.currency.upper(),
        max_reports=data.max_reports,
        is_active=True,
    )

    try:
        db.add(plan)
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        logger.exception("Failed to create subscription plan")
        raise HTTPException(500, "Creation failed")
    
    logger.info(f"Subscription plan created plan_id={plan.id}")

    return success_response(data=plan, message="Subscription plan created")


@router.post("/upload-excel", response_model=APIResponse[dict])
def upload_subscription_plans_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info("Admin uploading subscription plans via Excel")

    created_plans = add_subscription_plans_from_excel(
        db=db,
        file=file.file
    )

    return success_response(
        data={"created_plans": created_plans},
        message="Plans uploaded successfully"
    )
    

@router.put("/{plan_id}", response_model=APIResponse[SubscriptionPlanResponse])
def update_subscription_plan(
    plan_id: UUID,
    data: SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin updating subscription plan plan_id={plan_id}")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id
    ).first()

    if not plan:
        logger.warning(f"{SUBSCRIPTION_PLAN_NOT_FOUND} plan_id={plan_id}")
        raise HTTPException(404, SUBSCRIPTION_PLAN_NOT_FOUND)
    
    updates = data.model_dump(exclude_unset=True)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    try:
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        logger.exception("Failed to update subscription plan")
        raise HTTPException(500, "Update failed")
    
    logger.info(
        f"Subscription plan updated plan_id={plan.id} "
        f"fields={list(updates.keys())}"
    )

    return success_response(data=plan, message="Subscription plan updated")


@router.patch("/{plan_id}/toggle", response_model=APIResponse[dict])
def toggle_subscription_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin toggling subscription plan plan_id={plan_id}")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id
    ).first()

    if not plan:
        logger.warning(f"{SUBSCRIPTION_PLAN_NOT_FOUND} plan_id={plan_id}")
        raise HTTPException(404, SUBSCRIPTION_PLAN_NOT_FOUND)
    
    try:
        plan.is_active = not plan.is_active
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to toggle subscription plan")
        raise HTTPException(500, "Update failed")

    logger.info(
        f"Subscription plan status changed plan_id={plan.id} "
        f"is_active={plan.is_active}"
    )

    return success_response(
        data={"is_active": plan.is_active},
        message="Plan status updated"
    )
    
    
@router.delete("/{plan_id}", response_model=APIResponse[dict])
def delete_subscription_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin deleting subscription plan plan_id={plan_id}")

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id
    ).first()

    if not plan:
        logger.warning(f"{SUBSCRIPTION_PLAN_NOT_FOUND} plan_id={plan_id}")
        raise HTTPException(404, SUBSCRIPTION_PLAN_NOT_FOUND)

    try:
        db.delete(plan)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to delete subscription plan")
        raise HTTPException(500, "Deletion failed")

    logger.info(f"Subscription plan deleted plan_id={plan_id}")

    return success_response(
        data={"deleted": True},
        message="Subscription plan deleted successfully"
    )