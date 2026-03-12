# app/models/system_config.py

from sqlalchemy import DateTime
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, UniqueConstraint
from app.database.mixins import UUIDPrimaryKeyMixin
from app.database.db import Base


class SystemConfig(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "system_config"

    __table_args__ = (
        UniqueConstraint("config_key", name="uq_system_config_key"),
    )

    config_key = Column(String(150), nullable=False, unique=True, index=True)
    config_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)