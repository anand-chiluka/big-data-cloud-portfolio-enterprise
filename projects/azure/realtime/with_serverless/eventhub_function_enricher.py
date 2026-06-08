"""
STAR
Situation: Small Event Hubs messages need enrichment and validation before analytics ingestion.
Task: Build a serverless Azure Function for lightweight stream processing.
Action: Decode Event Hub records, validate required keys, enrich metadata, and return structured results.
Result: Demonstrates serverless real time processing without overusing Spark for small workloads.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def main(events: list[bytes]) -> list[dict]:
    """Azure Function style EventHubTrigger entrypoint."""
    enriched = []
    for raw in events:
        data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        if "event_id" not in data:
            raise ValueError("Missing event_id")
        data["processed_at"] = datetime.now(timezone.utc).isoformat()
        data["processor"] = "azure_eventhub_function_enricher"
        enriched.append(data)
    return enriched
