"""
Verification Adapter Registry for Part 5A
Provides a centralized registry and factory pattern to resolve verification adapters
by VerificationType and check source availability.
"""

import logging
from typing import Dict, List, Optional, Type

from app.verification.adapters.base import VerificationAdapter
from app.verification.adapters.internal_supporting import InternalSupportingDocumentAdapter
from app.verification.adapters.mock_bis import MockBISAdapter
from app.verification.adapters.mock_blacklisting import MockBlacklistingAdapter
from app.verification.adapters.mock_debarment import MockDebarmentAdapter
from app.verification.adapters.mock_dpiit import MockDPIITAdapter
from app.verification.adapters.mock_epfo import MockEPFOVerificationAdapter
from app.verification.adapters.mock_esic import MockESICVerificationAdapter
from app.verification.adapters.mock_gst import MockGSTVerificationAdapter
from app.verification.adapters.mock_local_content import MockLocalContentAdapter
from app.verification.adapters.mock_mca import MockMCAVerificationAdapter
from app.verification.adapters.mock_nsic import MockNSICVerificationAdapter
from app.verification.adapters.mock_oem import MockOEMAuthorizationAdapter
from app.verification.adapters.mock_pan import MockPANVerificationAdapter
from app.verification.adapters.mock_startup_india import MockStartupIndiaVerificationAdapter
from app.verification.adapters.mock_udyam import MockUdyamVerificationAdapter
from app.verification.types import VerificationType

logger = logging.getLogger(__name__)


class VerificationAdapterRegistry:
    """
    Thread-safe Central Registry of Verification Adapters.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, VerificationAdapter] = {}
        self._register_default_mock_adapters()

    def _register_default_mock_adapters(self) -> None:
        """Initializes standard Part 5A, 5B, 5C, 5D & 5E Adapters."""
        # Part 5B Adapters
        self.register_adapter(VerificationType.GST, MockGSTVerificationAdapter())
        self.register_adapter(VerificationType.PAN, MockPANVerificationAdapter())
        self.register_adapter(VerificationType.UDYAM, MockUdyamVerificationAdapter())

        # Part 5C Adapters
        self.register_adapter(VerificationType.MCA, MockMCAVerificationAdapter())
        self.register_adapter(VerificationType.STARTUP_INDIA, MockStartupIndiaVerificationAdapter())
        self.register_adapter(VerificationType.NSIC, MockNSICVerificationAdapter())
        self.register_adapter(VerificationType.EPFO, MockEPFOVerificationAdapter())
        self.register_adapter(VerificationType.ESIC, MockESICVerificationAdapter())

        # Part 5D Adapters
        self.register_adapter(VerificationType.OEM_AUTHORIZATION, MockOEMAuthorizationAdapter())
        self.register_adapter(VerificationType.LOCAL_CONTENT, MockLocalContentAdapter())
        self.register_adapter(VerificationType.BIS, MockBISAdapter())
        self.register_adapter(VerificationType.DPIIT, MockDPIITAdapter())
        self.register_adapter(VerificationType.SUPPORTING_DOCUMENT, InternalSupportingDocumentAdapter())

        # Part 5E Adapters
        self.register_adapter(VerificationType.BLACKLISTING, MockBlacklistingAdapter())
        self.register_adapter(VerificationType.DEBARMENT, MockDebarmentAdapter())

    def register_adapter(self, verification_type: str, adapter: VerificationAdapter) -> None:
        """
        Registers an adapter instance for a specific verification type.
        """
        self._adapters[verification_type.upper()] = adapter
        logger.info(
            "Registered verification adapter '%s' for type '%s'",
            adapter.source_name,
            verification_type,
        )

    def get_adapter(self, verification_type: str) -> Optional[VerificationAdapter]:
        """
        Resolves the configured adapter for the specified verification type.
        """
        return self._adapters.get(verification_type.upper())

    def is_type_supported(self, verification_type: str) -> bool:
        """
        Checks if an adapter is registered and ready for the given type.
        """
        return verification_type.upper() in self._adapters

    def list_supported_types(self) -> List[str]:
        """
        Returns list of all verification types currently supported by registered adapters.
        """
        return list(self._adapters.keys())

    def check_availability(self, verification_type: str) -> bool:
        """
        Checks if the adapter registered for this type is available.
        """
        adapter = self.get_adapter(verification_type)
        if not adapter:
            return False
        return adapter.is_available()


# Singleton global registry instance
adapter_registry = VerificationAdapterRegistry()
