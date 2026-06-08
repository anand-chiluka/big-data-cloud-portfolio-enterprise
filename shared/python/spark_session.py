"""
STAR
Situation: PySpark examples across clouds need a consistent local and managed session pattern.
Task: Avoid repeating Spark configuration in every job.
Action: Centralize session creation with adaptive execution, partition tuning, and extension hooks.
Result: Jobs remain easier to maintain while still allowing cloud specific overrides.
"""

from __future__ import annotations

from pyspark.sql import SparkSession


def build_spark(app_name: str, extra_conf: dict[str, str] | None = None) -> SparkSession:
    """Create a Spark session with safe defaults for batch and streaming jobs."""
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "200")
        .config("spark.sql.session.timeZone", "UTC")
    )

    for key, value in (extra_conf or {}).items():
        builder = builder.config(key, value)

    return builder.getOrCreate()
