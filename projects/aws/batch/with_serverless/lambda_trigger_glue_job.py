"""
STAR
Situation: S3 object arrival should start a managed Glue ETL job without running a scheduler.
Task: Build a Lambda handler that validates S3 events and submits a parameterized Glue job.
Action: Extract bucket and key, build an idempotent run id, and call Glue start_job_run.
Result: Demonstrates event driven batch orchestration using AWS serverless services.
"""

from __future__ import annotations

import hashlib
import os
from urllib.parse import unquote_plus

import boto3

GLUE = boto3.client("glue")
JOB_NAME = os.environ.get("GLUE_JOB_NAME", "orders_batch_lakehouse")


def build_run_id(bucket: str, key: str) -> str:
    """Create deterministic run id so duplicate S3 events are easy to identify."""
    digest = hashlib.sha256(f"{bucket}/{key}".encode("utf-8")).hexdigest()[:16]
    return f"s3_{digest}"


def lambda_handler(event, context):
    submitted = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        run_id = build_run_id(bucket, key)

        response = GLUE.start_job_run(
            JobName=JOB_NAME,
            Arguments={
                "--source_path": f"s3://{bucket}/{key}",
                "--run_id": run_id,
            },
        )
        submitted.append({"bucket": bucket, "key": key, "run_id": run_id, "job_run_id": response["JobRunId"]})

    return {"submitted": submitted}
