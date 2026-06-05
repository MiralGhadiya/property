# app/models/country.py

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class Country(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "countries"

    __table_args__ = (
        UniqueConstraint("name", name="uq_country_name"),
        UniqueConstraint("country_code", name="uq_country_country_code"),
    )

    name = Column(String, nullable=False)
    country_code = Column(String, unique=True, index=True)
    dial_code = Column(String, index=True)
    currency_code = Column(String, nullable=True)

    users = relationship("User", back_populates="country")
