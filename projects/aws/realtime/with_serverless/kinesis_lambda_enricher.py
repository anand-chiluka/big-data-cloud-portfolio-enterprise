"""
STAR
Situation: Low volume operational events in Kinesis need fast enrichment before landing in analytics storage.
Task: Build a serverless Kinesis Lambda processor with partial failure support.
Action: Decode records, validate payloads, enrich with processing metadata, and return failed item ids.
Result: Demonstrates lightweight real time serverless processing with safer retry behavior.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone


def enrich(record: dict) -> dict:
    """Add processing metadata while preserving the original payload."""
    record["processed_at"] = datetime.now(timezone.utc).isoformat()
    record["processor"] = "aws_kinesis_lambda_enricher"
    return record


def lambda_handler(event, context):
    failures = []
    outputs = []

    for record in event.get("Records", []):
        item_id = record.get("eventID", "unknown")
        try:
            payload = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
            data = json.loads(payload)
            outputs.append(enrich(data))
        except Exception:
            failures.append({"itemIdentifier": item_id})

    # In production, write outputs to Firehose, S3, DynamoDB, or another Kinesis stream.
    print(json.dumps({"processed": len(outputs), "failed": len(failures)}))
    return {"batchItemFailures": failures}
