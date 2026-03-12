from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Dict, Optional

class StaffBase(BaseModel):
    name: str  
    email: str  
    phone: str 
    password: str 
    role: str 
    
    
class StaffLogin(BaseModel):
    email: EmailStr
    password: str


class StaffCreate(StaffBase):
    can_access_user: bool = False
    can_access_staff: bool = False
    can_access_dashboard: bool = False
    can_access_reports: bool = False
    can_access_subscriptions_plans: bool = False
    can_access_config: bool = False


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    can_access_user: Optional[bool] = None
    can_access_staff: Optional[bool] = None
    can_access_dashboard: Optional[bool] = None
    can_access_reports: Optional[bool] = None
    can_access_subscriptions_plans: Optional[bool] = None
    can_access_config: Optional[bool] = None


class StaffResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str
    role: str
    accesses: Dict[str, bool]

    class Config:
        from_attributes = True