#app/routes/admin/feedback.py

from uuid import UUID
from sqlalchemy import or_
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query, HTTPException

from app.models.feedback import Feedback
from app.models.feedback_message import FeedbackMessage
from app.schemas import FeedbackResponse, AdminFeedbackAction

from app.common import PaginatedResponse

from app.utils.email import send_feedback_reply_email
from app.utils.response import APIResponse, success_response

from app.deps import get_db, require_superuser, pagination_params, require_management

from app.utils.logger_config import app_logger as logger


router = APIRouter(
    prefix="/admin/feedback",
    tags=["admin-feedback"]
)


@router.get("",
            response_model=APIResponse[PaginatedResponse[FeedbackResponse]]
        )
def list_feedback(
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
    params: dict = Depends(pagination_params),

    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    rating: Optional[int] = Query(None),
    valuation_id: Optional[str] = Query(None),
    subscription_id: Optional[int] = Query(None),
):
    logger.info(
        "Admin listing feedback "
        f"page={params['page']} status={status} type={type}"
    )

    query = db.query(Feedback)
    
    if user_id:
        query = query.filter(Feedback.user_id == user_id)
        
    if params["search"]:
        search = f"%{params['search']}%"
        query = query.filter(
            or_(
                Feedback.subject.ilike(search),
                Feedback.message.ilike(search),
                Feedback.valuation_id.ilike(search),
            )
        )

    if status:
        query = query.filter(Feedback.status == status)

    if type:
        query = query.filter(Feedback.type == type)
        
    if rating:
        query = query.filter(Feedback.rating == rating)

    if valuation_id:
        query = query.filter(Feedback.valuation_id == valuation_id)

    if subscription_id:
        query = query.filter(Feedback.subscription_id == subscription_id)

    total = query.count()

    # apply pagination safely
    if params["limit"] is not None:
        feedbacks = (
            query
            .order_by(Feedback.created_at.desc())
            .offset((params["page"] - 1) * params["limit"])
            .limit(params["limit"])
            .all()
        )
    else:
        feedbacks = query.order_by(Feedback.created_at.desc()).all()

    logger.debug(
        f"Admin fetched feedback count={len(feedbacks)} total={total}"
    )

    return success_response(
        data={
        "data": feedbacks,
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        },
    },
        message="Feedback list fetched successfully"
    )


@router.post("/{feedback_id}/action", response_model=APIResponse[dict])
def admin_feedback_action(
    feedback_id: UUID,
    data: AdminFeedbackAction,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id
    ).first()

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    did_reply = False

    if data.reply:
        msg = FeedbackMessage(
            feedback_id=feedback.id,
            sender="ADMIN",
            message=data.reply,
        )
        db.add(msg)
        did_reply = True

        if not data.status:
            feedback.status = "IN_PROGRESS"

    if data.status:
        feedback.status = data.status

    if data.admin_note is not None:
        feedback.admin_note = data.admin_note

    db.commit()

    if did_reply and data.notify_user:
        send_feedback_reply_email(
            to_email=feedback.user.email,
            feedback_id=feedback.id,
            reply=data.reply,
        )

    return success_response(
        data={
            "email_sent": did_reply and data.notify_user,
        },
        message="Feedback updated successfully"
    )


@router.get("/{feedback_id}", response_model=APIResponse[FeedbackResponse])
def get_feedback_by_id(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id
    ).first()

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    return success_response(data=feedback, message="Feedback retrieved successfully")


@router.delete("/{feedback_id}")
def delete_feedback(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_management),
):
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id
    ).first()

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    db.delete(feedback)
    db.commit()

    return success_response(message="Feedback deleted successfully")
