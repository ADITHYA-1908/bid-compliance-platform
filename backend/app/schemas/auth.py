import uuid
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of the user")
    email: str = Field(..., min_length=3, max_length=255, description="Valid work/personal email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)")
    organization_name: str = Field(..., min_length=2, max_length=255, description="Organization / Company name")
    organization_type: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default="BIDDER", description="Platform role: BIDDER, PROCUREMENT_OFFICER, ADMIN")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if not v:
            return "BIDDER"
        normalized = v.strip().upper()
        if normalized in ["PROCUREMENT", "OFFICER"]:
            normalized = "PROCUREMENT_OFFICER"
        if normalized not in ["BIDDER", "PROCUREMENT_OFFICER", "ADMIN"]:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: BIDDER, PROCUREMENT_OFFICER, ADMIN")
        return normalized


class BidderSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_name: str = Field(..., min_length=2, max_length=255)
    organization_type: Optional[str] = Field(default="Private Vendor", max_length=100)


class ProcurementSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_name: str = Field(..., min_length=2, max_length=255, description="Ministry / Government Department")
    organization_type: Optional[str] = Field(default="Government Ministry", max_length=100)


class AdminSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_name: str = Field(..., min_length=2, max_length=255, description="Platform Oversight Authority")
    organization_type: Optional[str] = Field(default="Platform Oversight", max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")
    expected_role: Optional[str] = Field(default=None, description="Optional role validation for role-isolated portals")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("expected_role")
    @classmethod
    def normalize_role(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        normalized = v.strip().upper()
        if normalized in ["PROCUREMENT", "OFFICER"]:
            normalized = "PROCUREMENT_OFFICER"
        return normalized


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    organization: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse
