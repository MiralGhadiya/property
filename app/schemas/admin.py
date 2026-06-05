# app/schemas/admin.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing_extensions import Literal


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str


class AdminProfile(BaseModel):
    id: UUID
    email: EmailStr
    username: str


class AdminUserResponse(BaseModel):
    id: UUID
    email: Optional[EmailStr]
    username: str
    mobile_number: str
    is_active: bool
    is_email_verified: bool
    is_superuser: bool
    role: str

    class Config:
        from_attributes = True


class AdminCreateUser(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    mobile_number: str
    password: str
    role: Optional[str] = "INDIVIDUAL"
    is_superuser: Optional[bool] = False


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    role: Optional[str] = None


class AdminResetPassword(BaseModel):
    new_password: str
    confirm_password: str


class AdminFeedbackAction(BaseModel):
    status: Optional[Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]] = None
    reply: Optional[str] = None
    notify_user: bool = False
    admin_note: Optional[str] = None


class AdminInquiryResponse(BaseModel):
    id: UUID
    type: str

    first_name: str
    last_name: Optional[str]

    email: str
    phone_number: Optional[str]

    message: str

    services: Optional[List[str]]
    # subscribe_newsletter: bool

    created_at: datetime

    model_config = {"from_attributes": True}  # IMPORTANT (Pydantic v2)


class UpdateSubscriptionDuration(BaseModel):
    duration_days: int


class CountryResponse(BaseModel):
    id: UUID
    name: str
    country_code: str
    dial_code: str
    currency_code: str | None

    class Config:
        from_attributes = True


class SystemConfigCreate(BaseModel):
    config_key: str
    config_value: Optional[str]
    description: Optional[str]


class SystemConfigUpdate(BaseModel):
    config_value: Optional[str]
    description: Optional[str]


class SystemConfigResponse(BaseModel):
    id: UUID
    config_key: str
    config_value: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


class EmptyObject(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {}})


class DashboardOverviewUserStats(BaseModel):
    total: int = Field(..., description="Total registered users.")
    active: int = Field(..., description="Users currently marked as active.")


class DashboardOverviewSubscriptionStats(BaseModel):
    total: int = Field(..., description="Total user subscriptions.")
    active: int = Field(..., description="Subscriptions currently active.")


class DashboardOverviewValuationStats(BaseModel):
    total: int = Field(..., description="Total valuation reports created.")


class DashboardOverviewResponse(BaseModel):
    users: DashboardOverviewUserStats
    subscriptions: DashboardOverviewSubscriptionStats
    valuations: DashboardOverviewValuationStats

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": {
                    "total": 184,
                    "active": 176,
                },
                "subscriptions": {
                    "total": 132,
                    "active": 128,
                },
                "valuations": {
                    "total": 945,
                },
            }
        }
    )


class DashboardUsersResponse(BaseModel):
    email_verified: int = Field(..., description="Users with verified email.")
    email_unverified: int = Field(..., description="Users without verified email.")
    inactive_users: int = Field(..., description="Users marked inactive.")
    new_users_last_30_days: int = Field(
        ...,
        description="Users whose email was verified in the last 30 days.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email_verified": 165,
                "email_unverified": 19,
                "inactive_users": 8,
                "new_users_last_30_days": 24,
            }
        }
    )


class DashboardUserRegistrationPoint(BaseModel):
    year: int = Field(..., description="Calendar year.")
    registrations: int = Field(..., description="Verified registrations for the year.")


class DashboardUserRegistrationsResponse(BaseModel):
    user_registrations_by_year: List[DashboardUserRegistrationPoint]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_registrations_by_year": [
                    {"year": 2022, "registrations": 18},
                    {"year": 2023, "registrations": 31},
                    {"year": 2024, "registrations": 42},
                    {"year": 2025, "registrations": 57},
                    {"year": 2026, "registrations": 24},
                ]
            }
        }
    )


class DashboardSubscriptionCountStats(BaseModel):
    total: int = Field(..., description="Total subscriptions for the plan.")
    active: int = Field(..., description="Active subscriptions for the plan.")


class DashboardSubscriptionRevenueStats(BaseModel):
    total: int = Field(
        ..., description="Total revenue from all subscriptions for the plan."
    )
    active: int = Field(..., description="Revenue from active subscriptions only.")


class DashboardSubscriptionBreakdownItem(BaseModel):
    country: str = Field(..., description="Country code assigned to the plan.")
    plan: str = Field(..., description="Subscription plan name.")
    currency: str = Field(..., description="Plan billing currency.")
    price: int = Field(..., description="Plan unit price.")
    subscriptions: DashboardSubscriptionCountStats
    revenue: DashboardSubscriptionRevenueStats

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "country": "AE",
                "plan": "PRO",
                "currency": "AED",
                "price": 999,
                "subscriptions": {
                    "total": 21,
                    "active": 19,
                },
                "revenue": {
                    "total": 20979,
                    "active": 18981,
                },
            }
        }
    )


class DashboardValuationCategoryPoint(BaseModel):
    category: str = Field(..., description="Valuation category or property type.")
    count: int = Field(..., description="Number of valuations in the category.")


class DashboardValuationsResponse(BaseModel):
    by_category: List[DashboardValuationCategoryPoint]
    last_30_days: int = Field(
        ..., description="Valuations created in the last 30 days."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "by_category": [
                    {"category": "apartment", "count": 84},
                    {"category": "villa", "count": 39},
                    {"category": "warehouse", "count": 11},
                ],
                "last_30_days": 43,
            }
        }
    )


class DashboardCountryCountPoint(BaseModel):
    country: str = Field(..., description="Country code.")
    count: int = Field(..., description="Total records for the country.")


class DashboardCountriesResponse(BaseModel):
    subscriptions: List[DashboardCountryCountPoint]
    valuations: List[DashboardCountryCountPoint]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subscriptions": [
                    {"country": "AE", "count": 52},
                    {"country": "IN", "count": 37},
                ],
                "valuations": [
                    {"country": "AE", "count": 71},
                    {"country": "IN", "count": 58},
                ],
            }
        }
    )


class DashboardFeedbackResponse(BaseModel):
    total_feedback: int = Field(..., description="Total feedback conversations.")
    open_feedback: int = Field(..., description="Feedback items still open.")
    avg_rating: float | None = Field(
        ...,
        description="Average rating across feedback entries with ratings.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_feedback": 94,
                "open_feedback": 7,
                "avg_rating": 4.37,
            }
        }
    )


class ValuationJsonBlob(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "country": "United Arab Emirates",
                "full_address": "Yas Island, Abu Dhabi, UAE",
                "property_type": "apartment",
                "built_up_area": "1250 sqft",
                "full_name": "John Doe",
                "email": "john@example.com",
            }
        },
    )


class ValuationAiResponseBlob(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "property_details": {
                    "address": "Yas Island, Abu Dhabi, UAE",
                    "property_type": "apartment",
                },
                "final_value_opinion": {
                    "market_value": 1850000,
                    "currency": "AED",
                },
                "forecast": None,
            }
        },
    )


class ValuationReportContextBlob(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "currency_code": "AED",
                "future_outlook": [],
                "property_maps": {"static_map_url": "https://maps.example/static-map"},
            }
        },
    )
