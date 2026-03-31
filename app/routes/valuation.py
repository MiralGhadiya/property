# app/routes/valuation.py

import uuid
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_
from sqlalchemy.orm import Session, undefer_group

from app.common import PaginatedResponse
from app.database.db import get_db
from app.deps import get_current_user, pagination_params
from app.models import User, ValuationReport
from app.models.valuation import (
    DesktopValuationForm,
    ValuationJob,
    desktop_valuation_form_dep,
)
from app.services.subscription_service import get_usable_subscription_with_fallback
from app.tasks.valuation_tasks import run_valuation_job, send_report_email_direct
from app.utils.date_filters import filter_by_date_range
from app.utils.logger_config import app_logger as logger
from app.utils.maps import geocode_address


router = APIRouter()


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

    if subscription.plan.country_code not in [detected_country, "GLOBAL", "DEFAULT"]:
        raise HTTPException(
            400,
            f"Resolved plan country ({subscription.plan.country_code}) "
            f"is not valid for property location ({detected_country})"
        )

    job = ValuationJob(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        subscription_id=subscription.id,
        category=category,
        request_payload=user_input,
        country_code=detected_country,
        status="processing",
    )

    try:
        db.add(job)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed creating valuation job")
        raise HTTPException(500, "Failed to create valuation job")

    try:
        result = await run_in_threadpool(run_valuation_job, job.id)
    except Exception:
        logger.exception(
            f"Direct valuation generation failed job_id={job.id} user_id={current_user.id}"
        )
        raise HTTPException(500, "Failed to generate valuation report")

    if not result:
        logger.error(f"Valuation completed without response job_id={job.id}")
        raise HTTPException(500, "Failed to generate valuation report")

    return result


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
    query = (
        db.query(
            ValuationReport.valuation_id,
            ValuationReport.category,
            ValuationReport.country_code,
            ValuationReport.created_at,
        )
        .filter(ValuationReport.user_id == current_user.id)
    )

    if category:
        query = query.filter(ValuationReport.category == category)

    if params["search"]:
        query = query.filter(
            or_(
                ValuationReport.valuation_id.ilike(f"%{params['search']}%"),
                ValuationReport.category.ilike(f"%{params['search']}%"),
                ValuationReport.country_code.ilike(f"%{params['search']}%"),
            )
        )

    query = filter_by_date_range(
        query,
        ValuationReport.created_at,
        from_date,
        to_date,
    )

    total = query.order_by(None).count()

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


@router.get("/valuation/{valuation_id}")
def get_valuation(
    valuation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valuation = (
        db.query(ValuationReport)
        .options(undefer_group("valuation_payload"))
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

    if job.status != "completed":
        return {
            "job_id": job.id,
            "status": job.status,
            "error": job.error_message,
        }

    valuation = (
        db.query(
            ValuationReport.valuation_id,
            ValuationReport.report_context,
        )
        .filter(
            ValuationReport.valuation_id == job.valuation_id,
            ValuationReport.user_id == current_user.id,
        )
        .first()
    )

    if not valuation:
        raise HTTPException(404, "Valuation not found")

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

    if pdf.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are allowed")

    content = await pdf.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5MB)")

    try:
        await run_in_threadpool(
            send_report_email_direct,
            valuation_id,
            current_user.id,
            content,
            pdf.filename,
        )
    except Exception:
        logger.exception(
            f"Direct report email failed valuation_id={valuation_id} user_id={current_user.id}"
        )
        raise HTTPException(500, "Failed to send report email")

    return {"message": "Email sent successfully"}
