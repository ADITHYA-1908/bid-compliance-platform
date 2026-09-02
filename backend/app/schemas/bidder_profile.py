import re
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Regular expression formats for Indian statutory identifiers
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PINCODE_REGEX = re.compile(r"^[1-9][0-9]{5}$")
UDYAM_REGEX = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$", re.IGNORECASE)


VALID_ORGANIZATION_TYPES = [
    "PROPRIETORSHIP",
    "PARTNERSHIP",
    "LLP",
    "PRIVATE_LIMITED",
    "PUBLIC_LIMITED",
    "GOVERNMENT_ENTITY",
    "STARTUP",
    "OTHER",
]

VALID_BUSINESS_CATEGORIES = [
    "MICRO",
    "SMALL",
    "MEDIUM",
    "LARGE",
    "OEM",
    "TRADER",
    "SERVICE_PROVIDER",
    "OTHER",
]


class ProfileCompletionInfo(BaseModel):
    completion_percentage: int = Field(..., ge=0, le=100, description="Percentage of required profile fields completed")
    is_complete: bool = Field(..., description="True if all required profile & organization fields are filled")
    missing_required_fields: List[str] = Field(default_factory=list, description="Human-readable names of missing mandatory fields")
    completed_fields_count: int = Field(..., ge=0)
    total_required_fields: int = Field(..., ge=1)


class BidderOrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    trade_name: Optional[str] = None
    organization_type: Optional[str] = None
    business_category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BidderOrganizationDetails(BaseModel):
    id: uuid.UUID
    name: str = Field(..., description="Legal Business / Entity Name")
    trade_name: Optional[str] = None
    organization_type: Optional[str] = None
    business_category: Optional[str] = None
    year_established: Optional[int] = None
    registration_number: Optional[str] = None
    registered_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = "India"
    official_email: Optional[str] = None
    official_phone: Optional[str] = None
    website: Optional[str] = None
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    cin_llpin: Optional[str] = None
    startup_india_number: Optional[str] = None
    nsic_number: Optional[str] = None
    epfo_code: Optional[str] = None
    esic_code: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BidderProfileDetails(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    role: str
    is_active: bool = True
    organization: Optional[BidderOrganizationSummary] = None

    model_config = ConfigDict(from_attributes=True)


class BidderProfileResponse(BaseModel):
    profile: BidderProfileDetails
    completion: ProfileCompletionInfo


class BidderOrganizationResponse(BaseModel):
    organization: BidderOrganizationDetails
    completion: ProfileCompletionInfo


class BidderProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=100)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Full name cannot be blank.")
        return v

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("designation")
    @classmethod
    def clean_designation(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class BidderOrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Legal Business Name")
    trade_name: Optional[str] = Field(None, max_length=255)
    organization_type: Optional[str] = Field(None, max_length=100)
    business_category: Optional[str] = Field(None, max_length=100)
    year_established: Optional[int] = Field(None, ge=1800, le=2100)
    registered_address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    official_email: Optional[str] = Field(None, max_length=255)
    official_phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    pan_number: Optional[str] = Field(None, max_length=20)
    gstin: Optional[str] = Field(None, max_length=25)
    udyam_number: Optional[str] = Field(None, max_length=50)
    cin_llpin: Optional[str] = Field(None, max_length=50)
    startup_india_number: Optional[str] = Field(None, max_length=50)
    nsic_number: Optional[str] = Field(None, max_length=50)
    epfo_code: Optional[str] = Field(None, max_length=50)
    esic_code: Optional[str] = Field(None, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Legal Business Name cannot be empty.")
        return v

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
            if not PAN_REGEX.match(v):
                raise ValueError("Invalid PAN format. Must be 10 characters (e.g. ABCDE1234F).")
        return v

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
            if not GSTIN_REGEX.match(v):
                raise ValueError("Invalid GSTIN format. Must be 15 characters (e.g. 29ABCDE1234F1Z5).")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not PINCODE_REGEX.match(v):
                raise ValueError("Invalid PIN code format. Must be 6 digits (e.g. 110001).")
        return v

    @field_validator("udyam_number")
    @classmethod
    def normalize_udyam(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
        return v

    @field_validator("official_email")
    @classmethod
    def validate_official_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Invalid email format.")
        return v

    @field_validator("trade_name", "registered_address", "city", "state", "country",
                     "official_phone", "website", "cin_llpin", "startup_india_number",
                     "nsic_number", "epfo_code", "esic_code")
    @classmethod
    def clean_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
