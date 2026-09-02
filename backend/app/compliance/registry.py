"""
Compliance Evaluator Registry for Part 6A, 6B, 6C, 6D & 6E
Registers and resolves domain-specific and generic compliance rule evaluators.
"""

from typing import List, Optional

from app.compliance.evaluators.base import ComplianceRuleEvaluator
from app.compliance.evaluators.generic import GenericRuleEvaluator
from app.compliance.evaluators.statutory import StatutoryRuleEvaluator
from app.compliance.evaluators.financial import FinancialComplianceEvaluator
from app.compliance.evaluators.experience import ExperienceComplianceEvaluator
from app.compliance.evaluators.technical import TechnicalComplianceEvaluator
from app.compliance.evaluators.oem import OEMComplianceEvaluator
from app.compliance.evaluators.local_content import LocalContentComplianceEvaluator
from app.compliance.evaluators.bis import BISComplianceEvaluator
from app.compliance.evaluators.document import SupportingDocumentEvaluator
from app.compliance.evaluators.integrity import IntegrityComplianceEvaluator
from app.compliance.types import (
    ComplianceContext,
    ComplianceRuleResult,
    ComplianceStatus,
)
from app.db.models.tender_requirement import TenderRequirement


class FallbackUnsupportedEvaluator(ComplianceRuleEvaluator):
    """
    Safe fallback evaluator for requirement types not yet implemented.
    Returns REVIEW without throwing unexpected runtime exceptions.
    """

    @property
    def evaluator_name(self) -> str:
        return "FallbackUnsupportedEvaluator"

    def supports(self, requirement: TenderRequirement) -> bool:
        return True

    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        return ComplianceRuleResult(
            compliance_status=ComplianceStatus.REVIEW,
            actual_value=None,
            expected_value=requirement.expected_value,
            operator=requirement.operator,
            reason=(
                f"EVALUATOR_NOT_IMPLEMENTED: No specialized compliance evaluator registered for "
                f"category='{requirement.category}', code='{requirement.code}'."
            ),
            evidence={"category": requirement.category, "code": requirement.code},
            source_verification_ids=[],
            is_mandatory=requirement.is_mandatory,
            is_critical=getattr(requirement, "is_critical", False) or False,
            weight=requirement.weight,
        )


class ComplianceEvaluatorRegistry:
    """
    Thread-safe registry for compliance rule evaluators.
    Evaluators are evaluated in registration order; specialized domain evaluators
    are registered before generic and fallback evaluators.
    """

    def __init__(self) -> None:
        self._evaluators: List[ComplianceRuleEvaluator] = []
        self._fallback_evaluator = FallbackUnsupportedEvaluator()

    def register(self, evaluator: ComplianceRuleEvaluator) -> None:
        """Registers a compliance rule evaluator."""
        self._evaluators.append(evaluator)

    def resolve_evaluator(self, requirement: TenderRequirement) -> ComplianceRuleEvaluator:
        """
        Resolves the highest-priority evaluator that supports the requirement.
        """
        for ev in self._evaluators:
            if ev.supports(requirement):
                return ev
        return self._fallback_evaluator

    def list_evaluators(self) -> List[str]:
        """Returns the list of registered evaluator names."""
        return [ev.evaluator_name for ev in self._evaluators]


# Global Registry Instance
compliance_registry = ComplianceEvaluatorRegistry()

# Register Domain Evaluators in Priority Order
compliance_registry.register(StatutoryRuleEvaluator())
compliance_registry.register(IntegrityComplianceEvaluator())
compliance_registry.register(FinancialComplianceEvaluator())
compliance_registry.register(ExperienceComplianceEvaluator())
compliance_registry.register(OEMComplianceEvaluator())
compliance_registry.register(LocalContentComplianceEvaluator())
compliance_registry.register(BISComplianceEvaluator())
compliance_registry.register(TechnicalComplianceEvaluator())
compliance_registry.register(SupportingDocumentEvaluator())
compliance_registry.register(GenericRuleEvaluator())
