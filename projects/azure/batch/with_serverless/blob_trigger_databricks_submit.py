"""
STAR
Situation: File arrival in Azure Blob or ADLS should trigger batch processing without a dedicated scheduler.
Task: Build an Azure Function that submits a Databricks job with the new blob path.
Action: Extract blob metadata, build a deterministic run id, and call the Databricks Jobs API.
Result: Demonstrates Azure serverless orchestration for big data batch workloads.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request


def main(blob_event: dict) -> dict:
    """Azure Function style entrypoint.

    Real Azure Functions can adapt this to a BlobTrigger or EventGridTrigger binding.
    """
    blob_url = blob_event["url"]
    run_id = hashlib.sha256(blob_url.encode("utf-8")).hexdigest()[:16]

    workspace_url = os.environ["DATABRICKS_WORKSPACE_URL"].rstrip("/")
    token = os.environ["DATABRICKS_TOKEN"]
    job_id = os.environ["DATABRICKS_JOB_ID"]

    payload = json.dumps(
        {
            "job_id": int(job_id),
            "notebook_params": {"source_path": blob_url, "run_id": run_id},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{workspace_url}/api/2.1/jobs/run-now",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    return {"run_id": run_id, "databricks_response": result}
