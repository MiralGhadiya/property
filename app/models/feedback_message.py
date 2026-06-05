# app/models/feedback_message.py

from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class FeedbackMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feedback_messages"

    feedback_id = Column(
        UUID(as_uuid=True),
        ForeignKey("feedback.id", ondelete="CASCADE"),
        nullable=False,
    )

    sender = Column(Enum("USER", "ADMIN", name="feedback_sender"), nullable=False)

    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
