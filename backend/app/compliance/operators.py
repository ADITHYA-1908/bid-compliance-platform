"""
Compliance Operator Evaluation Service for Part 6A
Provides deterministic, type-safe comparison operations across numbers (using Decimal),
dates (chronological normalization), strings (normalized matching), booleans, and presence.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple

from app.compliance.types import ComplianceOperator


def _to_decimal(val: Any) -> Optional[Decimal]:
    """Safely converts string/int/float/number to Decimal without precision loss."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "").replace("₹", "").replace("%", "").replace("INR", "").strip()
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def _to_date(val: Any) -> Optional[date]:
    """Safely converts ISO string or datetime/date object to date."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val_clean = val.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(val_clean, fmt).date()
            except ValueError:
                continue
    return None


def _to_boolean(val: Any) -> Optional[bool]:
    """Safely converts value to boolean."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        val_lower = val.strip().lower()
        if val_lower in ("true", "yes", "1", "y", "t", "active", "valid", "compliant", "verified"):
            return True
        if val_lower in ("false", "no", "0", "n", "f", "inactive", "invalid", "non-compliant", "cancelled", "expired"):
            return False
    return None


def compare_numbers(
    actual: Any,
    expected: Any,
    operator: str,
) -> Tuple[bool, Optional[str]]:
    """
    Compares two numeric values using Decimal arithmetic.
    Returns (result: bool, error_detail: Optional[str]).
    """
    act_dec = _to_decimal(actual)
    exp_dec = _to_decimal(expected)

    if act_dec is None or exp_dec is None:
        return False, f"Invalid numeric format: actual='{actual}', expected='{expected}'"

    op = operator.upper()
    if op in (ComplianceOperator.EQUALS, "EQ", "=="):
        return act_dec == exp_dec, None
    elif op in (ComplianceOperator.NOT_EQUALS, "NEQ", "!="):
        return act_dec != exp_dec, None
    elif op in (ComplianceOperator.GREATER_THAN, "GT", ">"):
        return act_dec > exp_dec, None
    elif op in (ComplianceOperator.GREATER_THAN_OR_EQUAL, "GTE", ">="):
        return act_dec >= exp_dec, None
    elif op in (ComplianceOperator.LESS_THAN, "LT", "<"):
        return act_dec < exp_dec, None
    elif op in (ComplianceOperator.LESS_THAN_OR_EQUAL, "LTE", "<="):
        return act_dec <= exp_dec, None
    else:
        return False, f"Unsupported numeric operator: '{operator}'"


def compare_dates(
    actual: Any,
    expected: Any,
    operator: str,
) -> Tuple[bool, Optional[str]]:
    """
    Compares two dates chronologically.
    Returns (result: bool, error_detail: Optional[str]).
    """
    act_dt = _to_date(actual)
    exp_dt = _to_date(expected)

    if act_dt is None or exp_dt is None:
        return False, f"Invalid date format: actual='{actual}', expected='{expected}'"

    op = operator.upper()
    if op in (ComplianceOperator.EQUALS, "EQ", "=="):
        return act_dt == exp_dt, None
    elif op in (ComplianceOperator.NOT_EQUALS, "NEQ", "!="):
        return act_dt != exp_dt, None
    elif op in (ComplianceOperator.GREATER_THAN, "GT", ">"):
        return act_dt > exp_dt, None
    elif op in (ComplianceOperator.GREATER_THAN_OR_EQUAL, "GTE", ">="):
        return act_dt >= exp_dt, None
    elif op in (ComplianceOperator.LESS_THAN, "LT", "<"):
        return act_dt < exp_dt, None
    elif op in (ComplianceOperator.LESS_THAN_OR_EQUAL, "LTE", "<="):
        return act_dt <= exp_dt, None
    else:
        return False, f"Unsupported date operator: '{operator}'"


def compare_strings(
    actual: Any,
    expected: Any,
    operator: str,
) -> Tuple[bool, Optional[str]]:
    """
    Compares text values with normalized trimming and case insensitivity.
    Supports EQUALS, NOT_EQUALS, CONTAINS, IN, and NOT_IN.
    """
    act_str = str(actual).strip() if actual is not None else ""
    op = (operator or "EQUALS").upper()

    if op in (ComplianceOperator.EQUALS, "EQ", "=="):
        exp_str = str(expected).strip() if expected is not None else ""
        return act_str.lower() == exp_str.lower(), None
    elif op in (ComplianceOperator.NOT_EQUALS, "NEQ", "!="):
        exp_str = str(expected).strip() if expected is not None else ""
        return act_str.lower() != exp_str.lower(), None
    elif op in (ComplianceOperator.CONTAINS, "LIKE"):
        exp_str = str(expected).strip() if expected is not None else ""
        return exp_str.lower() in act_str.lower(), None
    elif op in (ComplianceOperator.IN, "IN_LIST"):
        # Expected can be list/tuple/set or comma-separated string
        if isinstance(expected, (list, tuple, set)):
            target_list = [str(x).strip().lower() for x in expected]
        else:
            exp_raw = str(expected).strip()
            # Split on comma, semicolon, or slash
            target_list = [
                item.strip().lower()
                for item in exp_raw.replace("/", ",").replace(";", ",").replace("|", ",").split(",")
                if item.strip()
            ]
        return act_str.lower() in target_list, None
    elif op in (ComplianceOperator.NOT_IN, "NOT_IN_LIST"):
        if isinstance(expected, (list, tuple, set)):
            target_list = [str(x).strip().lower() for x in expected]
        else:
            exp_raw = str(expected).strip()
            target_list = [
                item.strip().lower()
                for item in exp_raw.replace("/", ",").replace(";", ",").replace("|", ",").split(",")
                if item.strip()
            ]
        return act_str.lower() not in target_list, None
    else:
        return False, f"Unsupported string operator: '{operator}'"


def compare_booleans(
    actual: Any,
    expected: Any,
    operator: str,
) -> Tuple[bool, Optional[str]]:
    """
    Compares boolean conditions.
    """
    act_bool = _to_boolean(actual)
    exp_bool = _to_boolean(expected)

    if act_bool is None or exp_bool is None:
        return False, f"Invalid boolean values: actual='{actual}', expected='{expected}'"

    op = operator.upper()
    if op in (ComplianceOperator.EQUALS, "EQ", "=="):
        return act_bool == exp_bool, None
    elif op in (ComplianceOperator.NOT_EQUALS, "NEQ", "!="):
        return act_bool != exp_bool, None
    else:
        return False, f"Unsupported boolean operator: '{operator}'"


def evaluate_exists(actual: Any, operator: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates existence/presence of a value (non-null, non-empty string, list, or dict).
    """
    has_value = False
    if actual is not None:
        if isinstance(actual, (str, list, dict)):
            has_value = len(actual) > 0
        else:
            has_value = True

    op = operator.upper()
    if op == ComplianceOperator.EXISTS:
        return has_value, None
    elif op == ComplianceOperator.NOT_EXISTS:
        return not has_value, None
    else:
        return False, f"Unsupported existence operator: '{operator}'"


def evaluate_generic_operator(
    actual: Any,
    expected: Any,
    operator: str,
    requirement_type: str = "TEXT",
) -> Tuple[bool, Optional[str]]:
    """
    Master dispatcher for generic operator evaluation based on requirement_type.
    """
    op = (operator or "EQUALS").upper()
    req_type = (requirement_type or "TEXT").upper()

    # Presence operators take precedence
    if op in (ComplianceOperator.EXISTS, ComplianceOperator.NOT_EXISTS):
        return evaluate_exists(actual, op)

    # Missing actual value handling
    if actual is None:
        return False, "Actual value is missing or None"

    if req_type in ("NUMBER", "NUMERIC", "FLOAT", "DECIMAL", "INTEGER", "CURRENCY", "PERCENTAGE"):
        return compare_numbers(actual, expected, op)

    if req_type in ("DATE", "DATETIME", "TIMESTAMP"):
        return compare_dates(actual, expected, op)

    if req_type in ("BOOLEAN", "BOOL"):
        return compare_booleans(actual, expected, op)

    if req_type in ("TEXT", "STRING", "STATUS", "CODE", "DOCUMENT", "REGISTRATION", "CERTIFICATION", "COMPLIANCE"):
        # If numeric operators are used on strings that look numeric, try number comparison first
        if op in (
            ComplianceOperator.GREATER_THAN,
            ComplianceOperator.GREATER_THAN_OR_EQUAL,
            ComplianceOperator.LESS_THAN,
            ComplianceOperator.LESS_THAN_OR_EQUAL,
        ):
            act_dec = _to_decimal(actual)
            exp_dec = _to_decimal(expected)
            if act_dec is not None and exp_dec is not None:
                return compare_numbers(actual, expected, op)

        return compare_strings(actual, expected, op)

    return False, f"Unknown requirement type '{requirement_type}'"
