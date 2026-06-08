"""
STAR
Situation: Small Pub/Sub messages need quick validation and enrichment without running Dataflow.
Task: Build a Cloud Function for lightweight event processing.
Action: Decode base64 Pub/Sub messages, validate payloads, enrich metadata, and log structured output.
Result: Demonstrates when to use serverless instead of a heavier streaming engine.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone


def entrypoint(event: dict, context) -> dict:
    raw = base64.b64decode(event["data"]).decode("utf-8")
    payload = json.loads(raw)
    if "event_id" not in payload:
        raise ValueError("Missing event_id")
    payload["processed_at"] = datetime.now(timezone.utc).isoformat()
    payload["processor"] = "gcp_pubsub_cloud_function_enricher"
    print(json.dumps(payload, sort_keys=True))
    return payload
