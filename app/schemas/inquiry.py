from typing import List, Optional

from pydantic import BaseModel, EmailStr


class InquiryCreate(BaseModel):
    type: str  # CONTACT or SERVICE

    first_name: str
    last_name: Optional[str] = None

    email: EmailStr
    phone_number: Optional[str] = None

    message: str

    services: Optional[List[str]] = None
    # subscribe_newsletter: Optional[bool] = False
