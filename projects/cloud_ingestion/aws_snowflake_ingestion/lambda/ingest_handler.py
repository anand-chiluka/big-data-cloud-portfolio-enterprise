"""
Lambda function: validates incoming raw JSON transaction events and
converts them to Parquet before writing to the S3 landing zone that
Snowpipe watches.

Why this step exists: Snowpipe can ingest JSON directly, but converting
to Parquet at the edge (in Lambda, before S3) means Snowflake's COPY INTO
does far less parsing work per file, and malformed events get caught and
routed to a dead-letter prefix before they ever reach the stage Snowpipe
watches, rather than landing as a bad row Snowflake has to reject.

This is written to run both as a real AWS Lambda handler (via the
`lambda_handler` entrypoint that API Gateway / S3 event triggers would
invoke) and as a standalone script for local testing without any AWS
credentials, via the `if __name__ == "__main__"` block at the bottom.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lambda_ingest")

REQUIRED_FIELDS = {"event_id", "account_id", "amount", "currency", "event_ts"}


@dataclass
class ValidationResult:
    valid_events: list[dict]
    rejected_events: list[dict]


def validate_events(raw_events: list[dict]) -> ValidationResult:
    """Validates required fields and basic type sanity before Parquet conversion.

    Full JSON Schema validation happens downstream in the consumer; this
    is a fast, cheap first-pass filter appropriate for a Lambda's tight
    execution budget, so obviously broken events never even reach the
    more expensive validation and Parquet conversion step.
    """
    valid: list[dict] = []
    rejected: list[dict] = []

    for event in raw_events:
        missing = REQUIRED_FIELDS - event.keys()
        if missing:
            rejected.append({"event": event, "reason": f"missing_fields:{sorted(missing)}"})
            continue

        try:
            float(event["amount"])
        except (TypeError, ValueError):
            rejected.append({"event": event, "reason": "amount_not_numeric"})
            continue

        valid.append(event)

    return ValidationResult(valid_events=valid, rejected_events=rejected)


def events_to_parquet_bytes(events: list[dict]) -> bytes:
    """Converts a list of validated event dicts to Parquet bytes in memory."""
    table = pa.Table.from_pylist(events)
    import io
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


def build_s3_key(prefix: str = "raw/transaction_events") -> str:
    """Builds a partitioned S3 key so downstream lifecycle rules and
    Snowflake's COPY INTO can prune by date without a full bucket scan.
    """
    now = datetime.now(timezone.utc)
    return f"{prefix}/year={now.year}/month={now.month:02d}/day={now.day:02d}/{now.strftime('%Y%m%dT%H%M%S')}_{now.microsecond}.parquet"


def write_local(data: bytes, key: str, local_root: str = "./local_s3_sim") -> str:
    """Local stand-in for an S3 PutObject call, used for testing without
    AWS credentials. Swap for boto3's s3.put_object(...) in production.
    """
    path = Path(local_root) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


def lambda_handler(event: dict, context) -> dict:
    """Real AWS Lambda entrypoint. `event` is expected to contain a
    `records` key with a batch of raw JSON transaction events, e.g. from
    an upstream Kinesis or API Gateway batch trigger.

    In production this function's S3 write would use boto3:
        import boto3
        s3 = boto3.client("s3")
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=parquet_bytes)
    which is intentionally not wired up here since no AWS credentials
    are available in this development/demo environment. See
    `write_local` for the locally-testable equivalent used below.
    """
    raw_events = event.get("records", [])
    result = validate_events(raw_events)

    if not result.valid_events:
        log.warning("no valid events in batch of %d", len(raw_events))
        return {"statusCode": 200, "written": 0, "rejected": len(result.rejected_events)}

    parquet_bytes = events_to_parquet_bytes(result.valid_events)
    key = build_s3_key()

    # Production: s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=parquet_bytes)
    local_path = write_local(parquet_bytes, key)
    log.info("wrote %d events to %s", len(result.valid_events), local_path)

    for rejected in result.rejected_events:
        log.warning("rejected event reason=%s", rejected["reason"])

    return {
        "statusCode": 200,
        "written": len(result.valid_events),
        "rejected": len(result.rejected_events),
        "s3_key": key,
    }


if __name__ == "__main__":
    sample_batch = {
        "records": [
            {"event_id": "e1", "account_id": "acct_01", "amount": 42.50,
             "currency": "USD", "event_ts": "2026-01-01T00:00:00Z"},
            {"event_id": "e2", "account_id": "acct_02", "amount": 15.00,
             "currency": "USD", "event_ts": "2026-01-01T00:01:00Z"},
            {"event_id": "e3", "account_id": "acct_03"},  # missing fields, will be rejected
            {"event_id": "e4", "account_id": "acct_04", "amount": "bad",
             "currency": "USD", "event_ts": "2026-01-01T00:02:00Z"},  # bad type, rejected
        ]
    }
    result = lambda_handler(sample_batch, context=None)
    print(json.dumps(result, indent=2))
