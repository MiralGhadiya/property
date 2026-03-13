#app/models/valuation.py

from fastapi import Form   
from typing import Optional 
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey

from sqlalchemy.dialects.postgresql import UUID
from app.database.mixins import UUIDPrimaryKeyMixin

from app.database.db import Base


class ValuationReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "valuation_reports"
    
    valuation_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")
    category = Column(String, nullable=False)    
    country_code = Column(String, nullable=False)  
    created_at = Column(DateTime, default=datetime.utcnow)
    user_fields = Column(JSON, nullable=False)
    ai_response = Column(JSON, nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("user_subscriptions.id"), nullable=False)
    report_context = Column(JSON, nullable=False)
    
    
class ValuationJob(UUIDPrimaryKeyMixin,Base):
    __tablename__ = "valuation_jobs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), nullable=False)
    category = Column(String, nullable=False)
    country_code = Column(String(5), nullable=False)

    request_payload = Column(JSON, nullable=False)

    status = Column(String, default="queued")  # queued | processing | completed | failed
    valuation_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())



class DesktopValuationForm(BaseModel):
    country: str
    full_address: str
    property_type: str
    land_area: Optional[str] = None
    built_up_area: Optional[str] = None
    year_built: Optional[str] = None
    
    # last_sale_date: Optional[str] = None
    # last_sale_price: Optional[str] = None
    ownership_type: Optional[str] = None

    configuration: Optional[str] = None
    construction_status: Optional[str] = None
    estimated_market_value: Optional[str] = None
    stories: Optional[str] = None
    purpose_of_valuation: str
    full_name: str
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    email: EmailStr
    contact_number: str
    
    
def desktop_valuation_form_dep(
    country: str = Form(...),
    # city_location: str = Form(...),
    full_address: str = Form(...),
    property_type: str = Form(...),
    land_area: str = Form(None),
    built_up_area: Optional[str] = Form(None),
    year_built: Optional[str] = Form(None),
    # last_sale_date: Optional[str] = Form(None),
    # last_sale_price: Optional[str] = Form(None),
    ownership_type: Optional[str] = Form(None),
    configuration: Optional[str] = Form(None),
    construction_status: Optional[str] = Form(None),
    estimated_market_value: Optional[str] = Form(None),
    stories: Optional[str] = Form(None),
    purpose_of_valuation: str = Form(...),
    full_name: str = Form(...),
    client_name: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    email: EmailStr = Form(...),
    contact_number: str = Form(...),
) -> DesktopValuationForm:
    return DesktopValuationForm(
        country=country,
        # city_location=city_location,
        full_address=full_address,
        property_type=property_type,
        land_area=land_area,
        built_up_area=built_up_area,
        year_built=year_built,
        # last_sale_date=last_sale_date,
        # last_sale_price=last_sale_price,
        ownership_type=ownership_type,
        configuration=configuration,
        construction_status=construction_status,
        estimated_market_value=estimated_market_value,
        stories=stories,
        purpose_of_valuation=purpose_of_valuation,
        full_name=full_name,
        client_name=client_name,
        project_name=project_name,
        email=email,
        contact_number=contact_number,
    )
