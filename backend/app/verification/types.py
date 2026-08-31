"""
Verification Types, Statuses, and Enums for Part 5A
Provides centralized identifiers, life-cycle statuses, match classifications,
claim origins, and normalized error codes for the Verification Engine.
"""

from typing import List


class VerificationType:
    GST = "GST"
    PAN = "PAN"
    UDYAM = "UDYAM"
    MCA = "MCA"
    STARTUP_INDIA = "STARTUP_INDIA"
    NSIC = "NSIC"
    EPFO = "EPFO"
    ESIC = "ESIC"
    OEM_AUTHORIZATION = "OEM_AUTHORIZATION"
    LOCAL_CONTENT = "LOCAL_CONTENT"
    BIS = "BIS"
    DPIIT = "DPIIT"
    SUPPORTING_DOCUMENT = "SUPPORTING_DOCUMENT"
    BLACKLISTING = "BLACKLISTING"
    DEBARMENT = "DEBARMENT"
    CROSS_DOCUMENT = "CROSS_DOCUMENT"
    OTHER = "OTHER"

    ALL: List[str] = [
        GST,
        PAN,
        UDYAM,
        MCA,
        STARTUP_INDIA,
        NSIC,
        EPFO,
        ESIC,
        OEM_AUTHORIZATION,
        LOCAL_CONTENT,
        BIS,
        DPIIT,
        SUPPORTING_DOCUMENT,
        BLACKLISTING,
        DEBARMENT,
        CROSS_DOCUMENT,
        OTHER,
    ]


class VerificationStatus:
    """
    Centralized verification lifecycle statuses.
    Note: These reflect claim validation only, NEVER tender compliance qualification.
    """
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"

    ALL: List[str] = [
        PENDING,
        IN_PROGRESS,
        VERIFIED,
        NOT_VERIFIED,
        NEEDS_REVIEW,
        UNAVAILABLE,
        FAILED,
    ]


class VerificationSourceType:
    MOCK = "MOCK"
    SANDBOX = "SANDBOX"
    OFFICIAL_API = "OFFICIAL_API"
    THIRD_PARTY = "THIRD_PARTY"
    MANUAL = "MANUAL"
    INTERNAL = "INTERNAL"

    ALL: List[str] = [
        MOCK,
        SANDBOX,
        OFFICIAL_API,
        THIRD_PARTY,
        MANUAL,
        INTERNAL,
    ]


class VerificationMatchStatus:
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"

    ALL: List[str] = [
        MATCH,
        MISMATCH,
        PARTIAL_MATCH,
        NOT_APPLICABLE,
        UNKNOWN,
    ]


class VerificationClaimSource:
    DOCUMENT = "DOCUMENT"
    PROFILE = "PROFILE"
    BID = "BID"
    SYSTEM = "SYSTEM"
    CROSS_DOCUMENT = "CROSS_DOCUMENT"

    ALL: List[str] = [
        DOCUMENT,
        PROFILE,
        BID,
        SYSTEM,
        CROSS_DOCUMENT,
    ]


class VerificationTriggerSource:
    SYSTEM = "SYSTEM"
    BIDDER = "BIDDER"
    PROCUREMENT_OFFICER = "PROCUREMENT_OFFICER"
    ADMIN = "ADMIN"

    ALL: List[str] = [
        SYSTEM,
        BIDDER,
        PROCUREMENT_OFFICER,
        ADMIN,
    ]


class VerificationErrorCode:
    VERIFICATION_INPUT_MISSING = "VERIFICATION_INPUT_MISSING"
    VERIFICATION_INPUT_INVALID = "VERIFICATION_INPUT_INVALID"
    ADAPTER_NOT_FOUND = "ADAPTER_NOT_FOUND"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SOURCE_TIMEOUT = "SOURCE_TIMEOUT"
    SOURCE_RESPONSE_INVALID = "SOURCE_RESPONSE_INVALID"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
