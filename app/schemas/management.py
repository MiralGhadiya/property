# app/schemas/management.py

from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class ManagementProfile(BaseModel):
    id: UUID
    type: str  # "admin" or "staff"

    # Common
    email: Optional[str] = None

    # Admin fields
    username: Optional[str] = None

    # Staff fields
    name: Optional[str] = None
    role: Optional[str] = None
    accesses: Optional[Dict[str, bool]] = None
