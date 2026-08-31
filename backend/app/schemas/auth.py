import uuid
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of the user")
    email: str = Field(..., min_length=3, max_length=255, description="Valid work/personal email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)")
    organization_name: str = Field(..., min_length=2, max_length=255, description="Organization / Company name")
    organization_type: Optional[str] = Field(default="Vendor / Bidder", max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format.")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


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
