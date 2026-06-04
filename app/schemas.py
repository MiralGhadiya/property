from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    mobile_number: str
    password: str
    
class LogoutRequest(BaseModel):
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr
    

class AppleLogin(BaseModel):
    id_token: str
    code: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr | None
    mobile_number: str
    country: str

    class Config:
        from_attributes = True
        
        
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
        
        
class ForgotPassword(BaseModel):
    email: EmailStr


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str
    
    
class ResetPassword(BaseModel):
    token: str
    new_password: str
    confirm_password: str
    
    
class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminProfile(BaseModel):
    id: int
    email: EmailStr
    username: str
    
    
class AdminUserResponse(BaseModel):
    id: int
    email: Optional[EmailStr]
    username: str
    mobile_number: str
    is_active: bool
    is_email_verified: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class AdminResetPassword(BaseModel):
    new_password: str
    confirm_password: str
    
    
class SubscriptionPlanCreate(BaseModel):
    name: str
    country_code: str
    price: int
    currency: str
    max_reports: Optional[int] = None
    allowed_categories: List[str]


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    max_reports: Optional[int] = None
    allowed_categories: Optional[List[str]] = None


class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    country_code: str
    price: int
    currency: str
    max_reports: Optional[int]
    allowed_categories: List[str]
    is_active: bool

    class Config:
        from_attributes = True
        
        
class AssignSubscription(BaseModel):
    plan_id: int
    duration_days: int = 30
    pricing_country_code: Optional[str] = None


class UpdateSubscription(BaseModel):
    extend_days: Optional[int] = None
    reset_reports_used: Optional[bool] = False
    deactivate: Optional[bool] = False


class UserSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    plan_name: str
    pricing_country_code: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    reports_used: int
    is_active: bool

    class Config:
        from_attributes = True
        
        
class ValuationResponse(BaseModel):
    id: int
    valuation_id: str
    user_id: int
    category: str
    country_code: str
    subscription_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ValuationDetailResponse(ValuationResponse):
    user_fields: dict
    ai_response: dict
    report_context: dict
    

class FeedbackCreate(BaseModel):
    type: Literal["GENERAL", "VALUATION", "PAYMENT", "SUBSCRIPTION"]
    subject: str
    message: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    valuation_id: Optional[str] = None
    subscription_id: Optional[int] = None
    

class FeedbackResponse(BaseModel):
    id: int
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
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
       
        
class AdminFeedbackAction(BaseModel):
    status: Optional[
        Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    ] = None

    reply: Optional[str] = None
    notify_user: bool = False
    admin_note: Optional[str] = None


class FeedbackUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)