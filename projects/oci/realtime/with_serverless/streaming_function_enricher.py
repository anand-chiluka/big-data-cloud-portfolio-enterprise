"""
STAR
Situation: OCI Streaming records need lightweight validation and enrichment before downstream routing.
Task: Build an OCI Function for serverless event processing.
Action: Decode records, validate event id, add processing metadata, and return enriched payloads.
Result: Demonstrates an OCI native alternative to running Spark for small event transformations.
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from fdk import response


def handler(ctx, data: io.BytesIO | None = None):
    payload = json.loads(data.getvalue()) if data else {}
    if "event_id" not in payload:
        return response.Response(ctx, status_code=400, response_data=json.dumps({"error": "Missing event_id"}))
    payload["processed_at"] = datetime.now(timezone.utc).isoformat()
    payload["processor"] = "oci_streaming_function_enricher"
    return response.Response(ctx, response_data=json.dumps(payload))
