"""
Compliance Rule Evaluator Base Abstraction for Part 6A
Defines the uniform interface implemented by generic and domain-specific compliance evaluators.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from app.compliance.types import ComplianceContext, ComplianceRuleResult
from app.db.models.tender_requirement import TenderRequirement


class ComplianceRuleEvaluator(ABC):
    """
    Base contract for evaluating a TenderRequirement against verified bidder evidence.
    """

    @property
    @abstractmethod
    def evaluator_name(self) -> str:
        """Human-readable identifier for this evaluator."""
        pass

    @abstractmethod
    def supports(self, requirement: TenderRequirement) -> bool:
        """
        Determines if this evaluator handles the given TenderRequirement based on
        category, code, requirement_type, or description.
        """
        pass

    @abstractmethod
    def evaluate(
        self,
        requirement: TenderRequirement,
        context: ComplianceContext,
    ) -> ComplianceRuleResult:
        """
        Executes the compliance evaluation logic for the requirement using the provided context.
        Must return a structured ComplianceRuleResult.
        """
        pass

    def validate_requirement(self, requirement: TenderRequirement) -> Tuple[bool, Optional[str]]:
        """
        Validates whether the TenderRequirement is structurally well-formed for evaluation.
        Defaults to True.
        """
        if not requirement.code or not requirement.operator:
            return False, "Requirement missing code or operator"
        return True, None
