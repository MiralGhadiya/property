#app/schemas/admin.py

from uuid import UUID
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing_extensions import Literal


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str


class AdminProfile(BaseModel):
    id: UUID
    email: EmailStr
    username: str


class AdminUserResponse(BaseModel):
    id: UUID
    email: Optional[EmailStr]
    username: str
    mobile_number: str
    is_active: bool
    is_email_verified: bool
    is_superuser: bool
    role: str

    class Config:
        from_attributes = True


class AdminCreateUser(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    mobile_number: str
    password: str
    role: Optional[str] = "INDIVIDUAL"
    is_superuser: Optional[bool] = False


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    role: Optional[str] = None
    

class AdminResetPassword(BaseModel):
    new_password: str
    confirm_password: str


class AdminFeedbackAction(BaseModel):
    status: Optional[
        Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    ] = None
    reply: Optional[str] = None
    notify_user: bool = False
    admin_note: Optional[str] = None


class AdminInquiryResponse(BaseModel):
    id: UUID
    type: str

    first_name: str
    last_name: Optional[str]

    email: str
    phone_number: Optional[str]

    message: str

    services: Optional[List[str]]
    # subscribe_newsletter: bool

    created_at: datetime

    model_config = {
        "from_attributes": True  # IMPORTANT (Pydantic v2)
    }
    

class UpdateSubscriptionDuration(BaseModel):
    duration_days: int
    
    
class CountryResponse(BaseModel):
    id: UUID
    name: str
    country_code: str
    dial_code: str
    currency_code: str | None

    class Config:
        from_attributes = True
        
        
class SystemConfigCreate(BaseModel):
    config_key: str
    config_value: Optional[str]
    description: Optional[str]


class SystemConfigUpdate(BaseModel):
    config_value: Optional[str]
    description: Optional[str]


class SystemConfigResponse(BaseModel):
    id: UUID
    config_key: str
    config_value: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True