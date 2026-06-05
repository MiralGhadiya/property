# app/models/feedback.py

from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class Feedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_user_created_at", "user_id", "created_at"),
        Index("ix_feedback_status_created_at", "status", "created_at"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    type = Column(Enum("GENERAL", "VALUATION", "PAYMENT", "SUBSCRIPTION", name="feedback_type"), nullable=False)

    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    rating = Column(Integer, nullable=True)  # 1–5

    valuation_id = Column(String, nullable=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(
        Enum("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="feedback_status"),
        default="OPEN",
        index=True,
    )

    admin_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    user = relationship("User", backref="feedbacks", lazy="selectin")
