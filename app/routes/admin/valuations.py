# app/router/admin/valuations.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, undefer_group

from app.common import PaginatedResponse
from app.deps import get_db, pagination_params, require_management
from app.models import User
from app.models.valuation import ValuationReport
from app.schemas import EmptyObject, ValuationDetailResponse, ValuationResponse
from app.utils.date_filters import filter_by_date_range
from app.utils.logger_config import app_logger as logger
from app.utils.response import APIResponse, success_response

router = APIRouter(prefix="/admin", tags=["admin-valuations"])


LIST_VALUATIONS_EXAMPLE = {
    "success": True,
    "message": "Valuations fetched successfully",
    "data": {
        "data": [
            {
                "id": "b1115df4-038f-4cea-9d39-a09d16138801",
                "valuation_id": "DV-20260325-0001",
                "user_id": "97d39a40-6cf6-4f8a-8a7e-0b33778c44bb",
                "category": "apartment",
                "country_code": "AE",
                "subscription_id": "f42c8032-6e4e-4c8c-8d16-31fbe8d0678f",
                "created_at": "2026-03-25T14:05:33.000000Z",
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 50,
            "total": 1,
        },
    },
}

VALUATION_DETAIL_EXAMPLE = {
    "success": True,
    "message": "Valuation details fetched successfully",
    "data": {
        "id": "b1115df4-038f-4cea-9d39-a09d16138801",
        "valuation_id": "DV-20260325-0001",
        "user_id": "97d39a40-6cf6-4f8a-8a7e-0b33778c44bb",
        "category": "apartment",
        "country_code": "AE",
        "subscription_id": "f42c8032-6e4e-4c8c-8d16-31fbe8d0678f",
        "created_at": "2026-03-25T14:05:33.000000Z",
        "user_fields": {
            "country": "United Arab Emirates",
            "full_address": "Yas Island, Abu Dhabi, UAE",
            "property_type": "apartment",
            "built_up_area": "1250 sqft",
            "full_name": "John Doe",
            "email": "john@example.com",
        },
        "ai_response": {
            "property_details": {
                "address": "Yas Island, Abu Dhabi, UAE",
                "property_type": "apartment",
            },
            "final_value_opinion": {
                "market_value": 1850000,
                "currency": "AED",
            },
            "forecast": None,
        },
        "report_context": {
            "currency_code": "AED",
            "future_outlook": [],
            "property_maps": {
                "static_map_url": "https://maps.example/static-map",
            },
        },
    },
}

DELETE_VALUATION_EXAMPLE = {
    "success": True,
    "message": "Valuation deleted successfully",
    "data": {},
}


@router.get(
    "/valuations",
    response_model=APIResponse[PaginatedResponse[ValuationResponse]],
    summary="List valuations",
    description=(
        "Returns valuation reports for admins and staff. Supports pagination, text search, "
        "country/category filters, date range filters, and sorting by supported fields."
    ),
    responses={
        200: {
            "description": "Paginated valuation list.",
            "content": {
                "application/json": {
                    "example": LIST_VALUATIONS_EXAMPLE,
                }
            },
        }
    },
)
def list_valuations(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    params: dict = Depends(pagination_params),
    user_id: Optional[UUID] = Query(
        None,
        description="Filter valuations by the owning user's UUID.",
    ),
    country_code: Optional[str] = Query(
        None,
        description="Filter by the detected property country code, for example `AE` or `IN`.",
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by valuation category. This matches the stored property type.",
    ),
    from_date: Optional[datetime] = Query(
        None,
        description="Include valuations created at or after this UTC datetime.",
    ),
    to_date: Optional[datetime] = Query(
        None,
        description="Include valuations created at or before this UTC datetime.",
    ),
    sort_by: str = Query(
        "created_at",
        description="Sort field. Allowed values: `created_at`, `valuation_id`, `category`, `country_code`.",
    ),
    order: str = Query(
        "desc",
        description="Sort order. Allowed values: `asc` or `desc`.",
    ),
):
    logger.info(
        "Admin listing valuations "
        f"page={params['page']} limit={params['limit']} "
        f"search={params['search']} user_id={user_id}"
    )

    query = db.query(
        ValuationReport.id,
        ValuationReport.valuation_id,
        ValuationReport.user_id,
        ValuationReport.category,
        ValuationReport.country_code,
        ValuationReport.subscription_id,
        ValuationReport.created_at,
    )

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
        query = query.filter(ValuationReport.country_code == country_code.upper())

    if category:
        query = query.filter(ValuationReport.category == category)

    query = filter_by_date_range(
        query,
        ValuationReport.created_at,
        from_date,
        to_date,
    )

    total = query.order_by(None).count()

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
            query.offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        valuations = query.all()

    logger.debug(f"Admin fetched valuations count={len(valuations)} total={total}")

    return success_response(
        data={
            "data": [
                {
                    "id": valuation.id,
                    "valuation_id": valuation.valuation_id,
                    "user_id": valuation.user_id,
                    "category": valuation.category,
                    "country_code": valuation.country_code,
                    "subscription_id": valuation.subscription_id,
                    "created_at": valuation.created_at,
                }
                for valuation in valuations
            ],
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            },
        },
        message="Valuations fetched successfully",
    )


@router.get(
    "/valuations/{valuation_id}",
    response_model=APIResponse[ValuationDetailResponse],
    summary="Get valuation details",
    description=(
        "Fetches the full valuation record, including the original input payload, "
        "AI response, and report context, using the public `valuation_id`."
    ),
    responses={
        200: {
            "description": "Full valuation payload.",
            "content": {
                "application/json": {
                    "example": VALUATION_DETAIL_EXAMPLE,
                }
            },
        }
    },
)
def get_valuation_details(
    valuation_id: str = Path(
        ...,
        description="Public valuation reference such as `DV-20260325-0001`.",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin fetching valuation valuation_id={valuation_id}")
    valuation = (
        db.query(ValuationReport)
        .options(undefer_group("valuation_payload"))
        .filter(ValuationReport.valuation_id == valuation_id)
        .first()
    )

    if not valuation:
        logger.warning(f"Valuation not found valuation_id={valuation_id}")
        raise HTTPException(404, "Valuation not found")

    return success_response(
        data=valuation, message="Valuation details fetched successfully"
    )


@router.get(
    "/users/{user_id}/valuations",
    response_model=APIResponse[PaginatedResponse[ValuationResponse]],
    summary="List valuations for a user",
    description=(
        "Returns valuation reports belonging to a single user. Supports the shared pagination "
        "and search parameters, and sorts newest valuations first."
    ),
    responses={
        200: {
            "description": "Paginated valuation list for the user.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User valuations fetched successfully",
                        "data": LIST_VALUATIONS_EXAMPLE["data"],
                    },
                }
            },
        }
    },
)
def get_user_valuations(
    user_id: UUID = Path(
        ...,
        description="UUID of the user whose valuations should be returned.",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    params: dict = Depends(pagination_params),
):

    logger.info(f"Admin fetching valuations user_id={user_id} page={params['page']}")

    user = db.get(User, user_id)
    if not user:
        logger.warning(f"User not found while fetching valuations user_id={user_id}")
        raise HTTPException(404, "User not found")

    query = db.query(
        ValuationReport.id,
        ValuationReport.valuation_id,
        ValuationReport.user_id,
        ValuationReport.category,
        ValuationReport.country_code,
        ValuationReport.subscription_id,
        ValuationReport.created_at,
    ).filter(ValuationReport.user_id == user_id)

    if params["search"]:
        query = query.filter(
            ValuationReport.valuation_id.ilike(f"%{params['search']}%")
        )

    total = query.order_by(None).count()

    if params["limit"] is not None:
        valuations = (
            query.order_by(ValuationReport.created_at.desc())
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        valuations = query.order_by(ValuationReport.created_at.desc()).all()

    return success_response(
        data={
            "data": [
                {
                    "id": valuation.id,
                    "valuation_id": valuation.valuation_id,
                    "user_id": valuation.user_id,
                    "category": valuation.category,
                    "country_code": valuation.country_code,
                    "subscription_id": valuation.subscription_id,
                    "created_at": valuation.created_at,
                }
                for valuation in valuations
            ],
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            },
        },
        message="User valuations fetched successfully",
    )


@router.delete(
    "/valuations/{valuation_id}/delete",
    response_model=APIResponse[EmptyObject],
    summary="Delete valuation",
    description="Deletes a valuation report by its public `valuation_id`.",
    responses={
        200: {
            "description": "Deletion completed.",
            "content": {
                "application/json": {
                    "example": DELETE_VALUATION_EXAMPLE,
                }
            },
        }
    },
)
def delete_valuation(
    valuation_id: str = Path(
        ...,
        description="Public valuation reference such as `DV-20260325-0001`.",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    logger.info(f"Admin deleting valuation valuation_id={valuation_id}")

    valuation = (
        db.query(ValuationReport)
        .filter(ValuationReport.valuation_id == valuation_id)
        .first()
    )

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

    return success_response(data={}, message="Valuation deleted successfully")
