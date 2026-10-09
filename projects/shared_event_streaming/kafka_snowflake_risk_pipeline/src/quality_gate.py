"""
STAR
Situation: Valid-looking events can still be wrong in ways that only show up after enrichment.
Task: Gate rows before the sink with checks on the enriched output.
Action: Check score range, non-negative aggregates, and flag/score consistency, returning a reason instead of raising.
Result: Rows that fail the gate go to the dead-letter path with a reason, and good rows are never held up.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.enrichment import EnrichedEvent


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason_code: str = ""
    detail: str = ""


def check(row: EnrichedEvent) -> GateResult:
    if not 0 <= row.risk_score <= 100:
        return GateResult(False, "score_out_of_range", str(row.risk_score))
    if row.tx_count_5m < 1 or row.amount_sum_5m < row.event.amount - 0.01:
        return GateResult(False, "inconsistent_aggregates", f"count={row.tx_count_5m} sum={row.amount_sum_5m}")
    if row.risk_flags and row.risk_score == 0:
        return GateResult(False, "flags_without_score", ",".join(row.risk_flags))
    if not row.risk_flags and row.risk_score != 0:
        return GateResult(False, "score_without_flags", str(row.risk_score))
    return GateResult(True)
