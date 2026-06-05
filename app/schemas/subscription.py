# app/schemas/subscription.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SubscriptionPlanCreate(BaseModel):
    name: str
    country_code: str
    price: int
    currency: str
    max_reports: Optional[int] = None


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    max_reports: Optional[int] = None


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    country_code: str
    price: int
    currency: str
    max_reports: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


class AssignSubscription(BaseModel):
    plan_id: UUID
    duration_days: int = 30
    pricing_country_code: Optional[str] = None


class UpdateSubscription(BaseModel):
    extend_days: Optional[int] = None
    reset_reports_used: Optional[bool] = False
    deactivate: Optional[bool] = False


class UserSubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID
    plan_name: str
    pricing_country_code: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    reports_used: int
    is_active: bool

    class Config:
        from_attributes = True
