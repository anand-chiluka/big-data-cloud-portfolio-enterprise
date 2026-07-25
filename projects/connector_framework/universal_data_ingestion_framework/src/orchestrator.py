"""
Orchestrator: runs one or more connectors and writes their output to a
sink, logging a per-source summary. This is intentionally simple; in a
real deployment this loop would be triggered by Airflow/Dagster/Prefect
on a schedule, with each connector-sink pair as its own task so failures
in one source don't block the others.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .connectors.base import BaseConnector
from .sinks.base import BaseSink

log = logging.getLogger("orchestrator")


@dataclass
class RunSummary:
    source_name: str
    records_extracted: int
    records_written: int
    extraction_errors: int


def run_pipeline(connectors: list[BaseConnector], sink: BaseSink) -> list[RunSummary]:
    summaries = []

    for connector in connectors:
        result = connector.extract()
        written = sink.write(result.records)

        summary = RunSummary(
            source_name=result.source_name,
            records_extracted=result.success_count,
            records_written=written,
            extraction_errors=result.error_count,
        )
        summaries.append(summary)

        log.info(
            "source=%s extracted=%d written=%d errors=%d",
            summary.source_name, summary.records_extracted,
            summary.records_written, summary.extraction_errors,
        )

    return summaries
