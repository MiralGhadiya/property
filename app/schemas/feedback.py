# app/schemas/feedback.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Literal


class FeedbackCreate(BaseModel):
    type: Literal["GENERAL", "VALUATION", "PAYMENT", "SUBSCRIPTION"]
    subject: str
    message: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    valuation_id: Optional[str] = None
    subscription_id: Optional[UUID] = None


class FeedbackResponse(BaseModel):
    id: UUID
    type: str
    subject: str
    message: str
    rating: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackMessageCreate(BaseModel):
    message: str


class FeedbackMessageResponse(BaseModel):
    id: UUID
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
