"""
SLI/SLO definitions for the data platform, expressed as executable
config rather than a wiki page nobody re-reads. `check_slo()` can be run
in CI, in a scheduled monitor, or interactively, and returns a concrete
pass/fail plus the actual numbers, not just a threshold restated in prose.

Naming convention: every metric follows
  {namespace}.{connector_or_sink}.{measurement}_{unit}
e.g. `data_platform.sql_connector.extract_duration_seconds`,
so metrics are greppable and consistent across every project in this repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .metrics import MetricsRegistry


@dataclass
class SLODefinition:
    name: str
    description: str
    metric_name: str
    threshold: float
    comparison: str  # "lte" | "gte"
    unit: str


# --- The actual SLOs this platform is held to ---
# These numbers are illustrative starting points for a portfolio project,
# not numbers pulled from a real production system. In a real environment
# these would be set from historical p50/p95/p99 baselines and revisited
# quarterly, not picked once and left alone.

SLO_DEFINITIONS: list[SLODefinition] = [
    SLODefinition(
        name="extraction_latency",
        description="95% of connector extraction runs should complete within 30 seconds",
        metric_name="extract_duration_seconds",
        threshold=30.0,
        comparison="lte",
        unit="seconds",
    ),
    SLODefinition(
        name="data_freshness",
        description="Data should never be more than 15 minutes stale at query time",
        metric_name="staleness_seconds",
        threshold=900.0,
        comparison="lte",
        unit="seconds",
    ),
    SLODefinition(
        name="extraction_error_rate",
        description="Extraction error rate should stay below 5% of total records processed",
        metric_name="error_rate_pct",
        threshold=5.0,
        comparison="lte",
        unit="percent",
    ),
    SLODefinition(
        name="pipeline_availability",
        description="99.9% of scheduled pipeline runs should complete without a failure requiring manual intervention",
        metric_name="run_success_rate_pct",
        threshold=99.9,
        comparison="gte",
        unit="percent",
    ),
]


@dataclass
class SLOCheckResult:
    slo_name: str
    passed: bool
    actual_value: Optional[float]
    threshold: float
    comparison: str


def check_slo(slo: SLODefinition, metrics: MetricsRegistry) -> SLOCheckResult:
    points = metrics.get_points(slo.metric_name)
    if not points:
        return SLOCheckResult(slo.name, passed=False, actual_value=None,
                               threshold=slo.threshold, comparison=slo.comparison)

    # For latency/staleness-style SLOs, check the worst (max) observed value,
    # since an SLO is about the tail, not the average.
    actual = max(p.value for p in points)

    if slo.comparison == "lte":
        passed = actual <= slo.threshold
    else:
        passed = actual >= slo.threshold

    return SLOCheckResult(slo.name, passed=passed, actual_value=actual,
                           threshold=slo.threshold, comparison=slo.comparison)


def check_all_slos(metrics: MetricsRegistry) -> list[SLOCheckResult]:
    return [check_slo(slo, metrics) for slo in SLO_DEFINITIONS]
