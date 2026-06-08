"""
STAR
Situation: Data pipelines often fail late because bad records are not caught near ingestion.
Task: Provide lightweight validation helpers that can be reused across cloud projects.
Action: Implement required field, duplicate key, and numeric range checks with clear error messages.
Result: Jobs fail fast or quarantine data with a specific reason instead of producing silent corruption.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    rule_name: str
    message: str
    failed_count: int = 0


def require_fields(records: Iterable[Mapping[str, Any]], fields: list[str]) -> QualityResult:
    """Validate that every record has the required fields populated."""
    failed = 0
    for record in records:
        if any(record.get(field) in (None, "") for field in fields):
            failed += 1
    return QualityResult(
        passed=failed == 0,
        rule_name="require_fields",
        message="All required fields are present" if failed == 0 else f"{failed} records missing required fields",
        failed_count=failed,
    )


def duplicate_keys(records: Iterable[Mapping[str, Any]], key: str) -> QualityResult:
    """Detect duplicate business keys in a small in memory dataset."""
    counts = Counter(str(record.get(key)) for record in records)
    failed = sum(1 for value in counts.values() if value > 1)
    return QualityResult(
        passed=failed == 0,
        rule_name="duplicate_keys",
        message="No duplicate keys found" if failed == 0 else f"{failed} duplicate keys found",
        failed_count=failed,
    )


def require_numeric_range(records: Iterable[Mapping[str, Any]], field: str, minimum: float, maximum: float) -> QualityResult:
    """Validate numeric values without depending on Spark."""
    failed = 0
    for record in records:
        try:
            value = float(record[field])
        except (KeyError, TypeError, ValueError):
            failed += 1
            continue
        if value < minimum or value > maximum:
            failed += 1
    return QualityResult(
        passed=failed == 0,
        rule_name="require_numeric_range",
        message="Values inside expected range" if failed == 0 else f"{failed} values outside expected range",
        failed_count=failed,
    )
