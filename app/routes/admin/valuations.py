# app/router/admin/valuations.py

from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_db, require_superuser, require_management

from app.models import User
from app.models.valuation import ValuationReport

from app.schemas import ValuationResponse, ValuationDetailResponse

from app.common import PaginatedResponse
from app.deps import pagination_params

from app.utils.date_filters import filter_by_date_range
from app.utils.response import APIResponse, success_response

from app.utils.logger_config import app_logger as logger


router = APIRouter(
    prefix="/admin",
    tags=["admin-valuations"]
)


@router.get("/valuations", response_model=APIResponse[PaginatedResponse[ValuationResponse]])
def list_valuations(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    
    params: dict = Depends(pagination_params),

    user_id: Optional[int] = Query(None),
    country_code: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),

):
    logger.info(
        "Admin listing valuations "
        f"page={params['page']} limit={params['limit']} "
        f"search={params['search']} user_id={user_id}"
    )
    
    query = db.query(ValuationReport)

    if params["search"]:
        query = query.filter(
            or_(
                ValuationReport.valuation_id.ilike(f"%{params['search']}%"),
                ValuationReport.category.ilike(f"%{params['search']}%"),
                ValuationReport.country_code.ilike(f"%{params['search']}%"),
            )
        )
    
    # 🔎 FILTERS
    if user_id:
        query = query.filter(ValuationReport.user_id == user_id)

    if country_code:
        query = query.filter(
            ValuationReport.country_code == country_code.upper()
        )

    if category:
        query = query.filter(
            ValuationReport.category.ilike(category)
        )

    query = filter_by_date_range(
            query,
            ValuationReport.created_at,
            from_date,
            to_date,
        )

    total = query.count()

    ALLOWED_SORT_FIELDS = {
        "created_at": ValuationReport.created_at,
        "valuation_id": ValuationReport.valuation_id,
        "category": ValuationReport.category,
        "country_code": ValuationReport.country_code,
    }

    sort_column = ALLOWED_SORT_FIELDS.get(sort_by)
    if not sort_column:
        raise HTTPException(400, "Invalid sort field")

    if order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    elif order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        raise HTTPException(400, "Invalid sort order")

    # 📄 PAGINATION
    if params["limit"] is not None:
        valuations = (
            query
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        valuations = query.all()

    logger.debug(
        f"Admin fetched valuations count={len(valuations)} total={total}"
    )

    return success_response(
        data={
            "data": valuations,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            }
        },
        message="Valuations fetched successfully"
    )


@router.get("/valuations/{valuation_id}", response_model=APIResponse[ValuationDetailResponse])
def get_valuation_details(
    valuation_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin fetching valuation valuation_id={valuation_id}")
    valuation = db.query(ValuationReport).filter(
        ValuationReport.valuation_id == valuation_id
    ).first()

    if not valuation:
        logger.warning(f"Valuation not found valuation_id={valuation_id}")
        raise HTTPException(404, "Valuation not found")

    return success_response(
        data=valuation,
        message="Valuation details fetched successfully"
    )


@router.get("/users/{user_id}/valuations", response_model=APIResponse[PaginatedResponse[ValuationResponse]])
def get_user_valuations(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    params : dict = Depends(pagination_params),
):
    
    logger.info(
        f"Admin fetching valuations user_id={user_id} "
        f"page={params['page']}"
    )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User not found while fetching valuations user_id={user_id}")
        raise HTTPException(404, "User not found")

    query = (
        db.query(ValuationReport)
        .filter(ValuationReport.user_id == user_id)
    )

    if params["search"]:
        query = query.filter(
            ValuationReport.valuation_id.ilike(
                f"%{params['search']}%"
            )
        )

    total = query.count()

    if params["limit"] is not None:
        valuations = (
            query
            .order_by(ValuationReport.created_at.desc())
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        valuations = query.order_by(ValuationReport.created_at.desc()).all()

    return success_response(
        data={
            "data": valuations,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            }
        },
        message="User valuations fetched successfully"
    )


@router.delete("/valuations/{valuation_id}/delete", response_model=APIResponse[dict])
def delete_valuation(
    valuation_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin deleting valuation valuation_id={valuation_id}")
    
    valuation = db.query(ValuationReport).filter(
        ValuationReport.valuation_id == valuation_id
    ).first()

    if not valuation:
        logger.warning(f"Valuation not found during delete valuation_id={valuation_id}")
        raise HTTPException(404, "Valuation not found")

    try:
        db.delete(valuation)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(f"Failed to delete valuation valuation_id={valuation_id}")
        raise HTTPException(500, "Deletion failed")
    
    logger.info(f"Valuation deleted valuation_id={valuation_id}")

    return success_response(
        data={},
        message="Valuation deleted successfully"
    )