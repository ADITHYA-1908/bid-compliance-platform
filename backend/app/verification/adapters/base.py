"""
Base Verification Adapter Interface and DTOs for Part 5A
Defines the standard contract that all verification adapters (Mock, Sandbox, Official)
must fulfill to integrate cleanly into the central Verification Engine.
"""

import abc
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.verification.types import (
    VerificationClaimSource,
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


@dataclass
class VerificationRequest:
    """
    Standardized payload submitted to a VerificationAdapter.
    """
    verification_type: str
    claimed_value: Any
    claim_source: str = VerificationClaimSource.DOCUMENT
    supporting_claims: Dict[str, Any] = field(default_factory=dict)
    bid_id: Optional[uuid.UUID] = None
    bid_document_id: Optional[uuid.UUID] = None
    document_processing_id: Optional[uuid.UUID] = None
    extra_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """
    Standardized output produced by a VerificationAdapter.
    """
    verification_type: str
    verification_status: str
    source_name: str
    source_type: str
    claimed_value: Any
    verified_value: Optional[Any] = None
    match_status: str = VerificationMatchStatus.UNKNOWN
    confidence: float = 1.0
    match_summary: Dict[str, str] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    normalized_claim_payload: Optional[Dict[str, Any]] = None
    normalized_verified_payload: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verification_type": self.verification_type,
            "verification_status": self.verification_status,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "claimed_value": self.claimed_value,
            "verified_value": self.verified_value,
            "match_status": self.match_status,
            "confidence": round(self.confidence, 2),
            "match_summary": self.match_summary,
            "evidence": self.evidence,
            "normalized_claim_payload": self.normalized_claim_payload,
            "normalized_verified_payload": self.normalized_verified_payload,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class VerificationAdapter(abc.ABC):
    """
    Abstract Base Class for Verification Adapters.
    Encapsulates source-specific communication, payload validation,
    and response normalization behind a uniform interface.
    """

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Human-readable provider/source name (e.g. 'Mock GST Registry')."""
        pass

    @property
    @abc.abstractmethod
    def source_type(self) -> str:
        """Type of source (e.g. VerificationSourceType.MOCK)."""
        pass

    @abc.abstractmethod
    def supports(self, verification_type: str) -> bool:
        """Returns True if this adapter can process the given verification type."""
        pass

    @abc.abstractmethod
    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validates claim format prior to dispatching to the source.
        Returns (is_valid, validation_error_message).
        """
        pass

    def is_available(self) -> bool:
        """
        Health/liveness check for the upstream source.
        Default is True for local/mock adapters.
        """
        return True

    @abc.abstractmethod
    async def verify(self, request: VerificationRequest) -> VerificationResult:
        """
        Executes verification against the underlying source and returns a normalized result.
        """
        pass
