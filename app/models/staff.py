# app/models/staff.py

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.db import Base


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    password = Column(String, nullable=False)

    can_access_user = Column(Boolean, default=False)  # User Access
    can_access_staff = Column(Boolean, default=False)  # Staff Access
    can_access_dashboard = Column(Boolean, default=False)  # Dashboard Access
    can_access_reports = Column(Boolean, default=False)  # Reports Access
    can_access_subscriptions_plans = Column(Boolean, default=False)  # Subscriptions & Plans Access
    can_access_config = Column(Boolean, default=False)

    # Relationship with user table if needed
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User", back_populates="staff_member")  # Add back_populates here
