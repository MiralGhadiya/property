from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.inquiry import Inquiry
from app.schemas.inquiry import InquiryCreate
from app.utils.logger_config import app_logger as logger

router = APIRouter(prefix="/inquiries", tags=["Public Inquiries"])


@router.post("")
def create_inquiry(
    data: InquiryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    logger.info(f"Inquiry received email={data.email} type={data.type}")

    try:
        inquiry = Inquiry(**data.model_dump())

        db.add(inquiry)
        db.commit()
        db.refresh(inquiry)

        # Optional: Send email to admin
        # send_admin_feedback_email(...)

        return {
            "message": "Thank you! We’ll get back to you shortly.",
            "inquiry_id": inquiry.id,
        }

    except Exception:
        db.rollback()
        logger.exception("Inquiry submission failed")
        raise HTTPException(500, "Failed to submit inquiry")
