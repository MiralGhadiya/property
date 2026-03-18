#app/schemas/user.py

from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    mobile_number: str
    password: str
    role: str


class UserResponse(UserBase):
    id: UUID
    is_active: bool

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    id: UUID
    username: str
    email: Optional[EmailStr]
    mobile_number: str
    country: Optional[str]
    role: str
    
    subscription_id: Optional[UUID] = None
    has_active_subscription: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
