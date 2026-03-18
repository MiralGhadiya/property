# app/routes/valuation.py

import base64
import uuid
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Depends,
    Form,
    Query,
    Request,
)
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.db import get_db
from app.common import PaginatedResponse
from app.deps import get_current_user, pagination_params
from app.models.country import Country
from app.tasks.valuation_tasks import process_valuation_job, send_report_email_task
from app.services.subscription_service import get_usable_subscription_with_fallback

from app.models import User, ValuationReport, subscription
from app.models.valuation import (
    DesktopValuationForm,
    ValuationJob,
    desktop_valuation_form_dep,
)
from app.utils.maps import geocode_address
from app.utils.date_filters import filter_by_date_range
from app.utils.logger_config import app_logger as logger


router = APIRouter()


# ==========================================================
# CREATE VALUATION (QUEUE JOB ONLY)
# ==========================================================
@router.post("/create")
async def create_valuation_form(
    request: Request,
    form: DesktopValuationForm = Depends(desktop_valuation_form_dep),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"Valuation request started user_id={current_user.id}"
    )

    try:
        user_input = form.model_dump()
    except Exception:
        logger.exception("Invalid valuation form data")
        raise HTTPException(400, "Invalid valuation input")

    category = user_input.get("property_type")
    if not category:
        raise HTTPException(400, "Invalid property type")

    address = user_input.get("full_address")
    if not address:
        raise HTTPException(400, "Property address is required")

    geo = geocode_address(address)

    if not geo or not geo.get("country_code"):
        raise HTTPException(400, "Unable to detect property country")

    detected_country = geo["country_code"]

    subscription = get_usable_subscription_with_fallback(
        db=db,
        user_id=current_user.id,
        country_code=detected_country,
    )

    if not subscription:
        raise HTTPException(
            status_code=403,
            detail=(
                f"No active subscription with remaining reports found for "
                f"{detected_country}. Please purchase a plan first."
            ),
        )

    if subscription.plan.country_code not in [detected_country, "DEFAULT"]:
        raise HTTPException(
            400,
            f"Resolved plan country ({subscription.plan.country_code}) "
            f"is not valid for property location ({detected_country})"
        )

    country_code = detected_country

    job = ValuationJob(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        subscription_id=subscription.id,
        category=category,
        request_payload=user_input,
        country_code=country_code,
        status="queued",
    )

    try:
        db.add(job)
        db.commit()

        process_valuation_job.delay(job.id)

    except Exception:
        db.rollback()
        logger.exception("Failed queuing valuation job")

        job.status = "failed"
        job.error_message = "Queue unavailable"
        db.add(job)
        db.commit()

        raise HTTPException(503, "Valuation service unavailable")

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Valuation job queued successfully",
        # "subscription_id": str(subscription.id),
        # "subscription_country": subscription.plan.country_code,
        # "reports_remaining": (
        #     None if subscription.plan.max_reports is None
        #     else subscription.plan.max_reports - subscription.reports_used - 1
        # ),
    }
    
    
# ==========================================================
# MY VALUATIONS
# ==========================================================
@router.get(
    "/my-valuations",
    response_model=PaginatedResponse[dict],
)
def my_valuations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    params: dict = Depends(pagination_params),
    category: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    query = db.query(ValuationReport).filter(
        ValuationReport.user_id == current_user.id
    )

    if category:
        query = query.filter(ValuationReport.category == category)

    if params["search"]:
        query = query.filter(
            or_(
                ValuationReport.valuation_id.ilike(
                    f"%{params['search']}%"
                ),
                ValuationReport.category.ilike(
                    f"%{params['search']}%"
                ),
                ValuationReport.country_code.ilike(
                    f"%{params['search']}%"
                ),
            )
        )

    query = filter_by_date_range(
        query,
        ValuationReport.created_at,
        from_date,
        to_date,
    )

    total = query.count()

    query = query.order_by(ValuationReport.created_at.desc())
    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"])
    
    records = query.all()

    return {
        "data": [
            {
                "valuation_id": v.valuation_id,
                "category": v.category,
                "country_code": v.country_code,
                "created_at": v.created_at,
            }
            for v in records
        ],
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        },
    }


# ==========================================================
# GET SINGLE VALUATION
# ==========================================================
@router.get("/valuation/{valuation_id}")
def get_valuation(
    valuation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valuation = (
        db.query(ValuationReport)
        .filter(
            ValuationReport.valuation_id == valuation_id,
            ValuationReport.user_id == current_user.id,
        )
        .first()
    )

    if not valuation:
        raise HTTPException(404, "Valuation not found")

    return {
        "valuation_id": valuation.valuation_id,
        "category": valuation.category,
        "country_code": valuation.country_code,
        "user_fields": valuation.user_fields,
        "ai_response": valuation.ai_response,
        "report_context": valuation.report_context,
        "created_at": valuation.created_at,
    }


# ==========================================================
# JOB STATUS (RETURNS OLD RESPONSE FORMAT WHEN DONE)
# ==========================================================
@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(ValuationJob)
        .filter(
            ValuationJob.id == job_id,
            ValuationJob.user_id == current_user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(404, "Job not found")

    # Still processing
    if job.status != "completed":
        return {
            "job_id": job.id,
            "status": job.status,
            "error": job.error_message,
        }

    # Completed → return EXACT old response structure
    valuation = (
        db.query(ValuationReport)
        .filter(
            ValuationReport.valuation_id == job.valuation_id,
            ValuationReport.user_id == current_user.id,
        )
        .first()
    )

    if not valuation:
        raise HTTPException(404, "Valuation not found")
    
    # country = (
    #     db.query(Country)
    #     .filter(Country.country_code == valuation.country_code)
    #     .first()
    # )

    # currency_code = country.currency_code if country else None
    
    currency_code = valuation.report_context.get("currency_code")

    return {
        "status": "success",
        "valuation_id": valuation.valuation_id,
        "report_context": valuation.report_context,
        "currency_code": currency_code,
    }


@router.post("/send-report")
async def send_report(
    valuation_id: str = Form(...),
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1️⃣ Validate valuation belongs to user
    valuation = (
        db.query(ValuationReport)
        .filter(
            ValuationReport.valuation_id == valuation_id,
            ValuationReport.user_id == current_user.id,
        )
        .first()
    )

    if not valuation:
        raise HTTPException(404, "Valuation not found")

    # 2️⃣ Validate file type
    if pdf.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are allowed")

    content = await pdf.read()

    # 3️⃣ File size limit (5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5MB)")

    # 4️⃣ Encode to Base64 (required because Celery uses JSON serializer)
    encoded_pdf = base64.b64encode(content).decode("utf-8")

    # 5️⃣ Push to Celery
    send_report_email_task.delay(
        valuation_id,
        current_user.id,
        encoded_pdf,
        pdf.filename,
    )

    return {"message": "Email queued successfully"}