#app/routers/user_feedback.py

from uuid import UUID
from sqlalchemy import or_
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import User
from app.models.feedback import Feedback
from app.models.feedback_message import FeedbackMessage

from app.common import PaginatedResponse
from app.schemas import FeedbackCreate, FeedbackResponse, FeedbackMessageCreate, FeedbackUpdate

from app.utils.email import send_admin_feedback_email
from app.deps import get_db, get_current_user, pagination_params

from app.utils.logger_config import app_logger as logger


router = APIRouter(
    prefix="/feedback",
    tags=["feedback"]
)


@router.post("")
def create_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"Feedback submission started user_id={current_user.id} "
        f"type={data.type}"
    )

    try:
        feedback = Feedback(
            user_id=current_user.id,
            **data.model_dump()
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        send_admin_feedback_email(feedback, current_user)

        logger.info(
            f"Feedback created feedback_id={feedback.id}"
            f"user_id={current_user.id}"
        )

        return {"message": "Feedback submitted successfully"}

    except Exception:
        db.rollback()
        logger.exception(
            f"Feedback creation failed user_id={current_user.id}"
        )
        raise HTTPException(500, "Failed to submit feedback")


@router.get(
    "/my",
    response_model=PaginatedResponse[FeedbackResponse]
)
def my_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    params: dict = Depends(pagination_params),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
):
    logger.info(
        f"Fetching user feedback user_id={current_user.id} "
        f"page={params['page']}"
    )

    query = db.query(Feedback).filter(
        Feedback.user_id == current_user.id
    )

    if params.get("search"):
        query = query.filter(
            or_(
                Feedback.subject.ilike(f"%{params['search']}%"),
                Feedback.message.ilike(f"%{params['search']}%"),
            )
        )

    if status:
        query = query.filter(Feedback.status == status)

    if type:
        query = query.filter(Feedback.type == type)

    total = query.count()

    query = query.order_by(Feedback.created_at.desc())
    if params["limit"] is not None:
        query = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"])
    
    feedbacks = query.all()

    return {
        "data": feedbacks,
        "pagination": {
            "page": params["page"],
            "limit": params["limit"],
            "total": total,
        },
    }
    

@router.get("/{feedback_id}", response_model=FeedbackResponse)
def get_my_feedback_by_id(
    feedback_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = (
        db.query(Feedback)
        .filter(
            Feedback.id == feedback_id,
            Feedback.user_id == current_user.id
        )
        .first()
    )

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    return feedback


@router.patch("/update/{feedback_id}", response_model=FeedbackResponse)
def update_my_feedback(
    feedback_id: UUID,
    data: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = (
        db.query(Feedback)
        .filter(
            Feedback.id == feedback_id,
            Feedback.user_id == current_user.id
        )
        .first()
    )

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    # Optional business rule: block updates after admin starts working
    if feedback.status != "OPEN":
        raise HTTPException(
            400,
            "Feedback can no longer be edited"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(feedback, field, value)

    db.commit()
    db.refresh(feedback)

    return feedback


@router.post("/{feedback_id}/messages")
def user_reply_feedback(
    feedback_id: UUID,
    data: FeedbackMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(404, "Feedback not found")

    msg = FeedbackMessage(
        feedback_id=feedback_id,
        sender="USER",
        message=data.message,
    )

    db.add(msg)
    db.commit()

    return {"message": "Reply sent"}