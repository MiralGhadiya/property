# app/models/user.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=True)
    role = Column(String, nullable=False, default="INDIVIDUAL")
    username = Column(String, index=True, nullable=False)
    mobile_number = Column(String, unique=True, index=True, nullable=False)
    country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"))
    hashed_password = Column(String, nullable=False)

    provider = Column(String, default="LOCAL", nullable=True)
    provider_id = Column(String, nullable=True, index=True)

    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True, index=True)

    country = relationship("Country", back_populates="users", lazy="selectin")

    is_superuser = Column(Boolean, default=False)

    staff_member = relationship("Staff", back_populates="user", uselist=False)
