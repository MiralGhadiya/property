# app/router/admin/inquiries.py

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime

from app.deps import get_db, pagination_params, require_management
from app.models.inquiry import Inquiry
from app.models import User
from app.schemas.admin import AdminInquiryResponse
from app.common import PaginatedResponse
from app.utils.date_filters import filter_by_date_range
from app.utils.response import APIResponse, success_response

router = APIRouter(
    prefix="/admin/inquiries",
    tags=["admin-inquiries"]
)


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[AdminInquiryResponse]]
)
def list_inquiries(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_management),
    params: dict = Depends(pagination_params),

    # Filters
    type: Optional[str] = Query(None),
    # subscribe_newsletter: Optional[bool] = Query(None),

    # Date filters
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),

    # Sorting
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    query = db.query(Inquiry)

    if params["search"]:
        search_term = f"%{params['search']}%"
        query = query.filter(
            or_(
                Inquiry.first_name.ilike(search_term),
                Inquiry.last_name.ilike(search_term),
                Inquiry.email.ilike(search_term),
                Inquiry.phone_number.ilike(search_term),
                Inquiry.message.ilike(search_term),
            )
        )

    if type:
        query = query.filter(Inquiry.type == type)

    query = filter_by_date_range(
        query,
        Inquiry.created_at,
        created_from,
        created_to,
    )

    total = query.count()

    ALLOWED_SORT_FIELDS = {
        "created_at": Inquiry.created_at,
        "first_name": Inquiry.first_name,
        "email": Inquiry.email,
        "type": Inquiry.type,
    }

    sort_column = ALLOWED_SORT_FIELDS.get(sort_by)

    if not sort_column:
        raise HTTPException(400, "Invalid sort field")

    if order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # apply pagination only when a limit is provided; otherwise return all results
    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"])\
                     .limit(params["limit"])
    inquiries = query.all()

    return success_response(
        data={
            "data": inquiries,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            }
        },
        message="Inquiries fetched successfully"
    )
