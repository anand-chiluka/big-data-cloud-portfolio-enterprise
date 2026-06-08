"""
STAR
Situation: Spark pipelines need consistent quality gates before writing curated data.
Task: Provide reusable DataFrame checks for required columns and null thresholds.
Action: Implement validation helpers that return counts and raise clear exceptions.
Result: Production jobs can stop bad data before it reaches trusted lakehouse tables.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


class SparkQualityError(RuntimeError):
    """Raised when a Spark quality gate fails."""


def assert_required_columns(df: DataFrame, required_columns: list[str]) -> None:
    """Ensure all required columns exist in a DataFrame."""
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise SparkQualityError(f"Missing required columns: {missing}")


def assert_not_null(df: DataFrame, columns: list[str], max_failed_rows: int = 0) -> None:
    """Fail when required columns exceed the allowed null count."""
    condition = None
    for column in columns:
        current = F.col(column).isNull()
        condition = current if condition is None else condition | current
    failed_rows = df.filter(condition).count() if condition is not None else 0
    if failed_rows > max_failed_rows:
        raise SparkQualityError(f"Null validation failed for {columns}. failed_rows={failed_rows}")
