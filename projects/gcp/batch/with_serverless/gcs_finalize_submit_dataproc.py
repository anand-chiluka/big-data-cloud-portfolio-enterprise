"""
STAR
Situation: GCS object finalization should trigger a Dataproc batch without running a scheduler.
Task: Build a Cloud Function that submits a Dataproc Serverless batch job.
Action: Parse the event, create a deterministic batch id, and call the Dataproc API.
Result: Demonstrates GCP serverless orchestration for batch Spark workloads.
"""

from __future__ import annotations

import hashlib
import os
from google.cloud import dataproc_v1


def entrypoint(event: dict, context) -> dict:
    bucket = event["bucket"]
    name = event["name"]
    source_path = f"gs://{bucket}/{name}"
    batch_id = "orders-" + hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:12]

    project_id = os.environ["GCP_PROJECT"]
    region = os.environ.get("DATAPROC_REGION", "us-central1")
    client = dataproc_v1.BatchControllerClient(client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"})

    batch = dataproc_v1.Batch(
        pyspark_batch=dataproc_v1.PySparkBatch(
            main_python_file_uri=os.environ["MAIN_PYTHON_FILE_URI"],
            args=["--source", source_path, "--run-id", batch_id],
        )
    )
    request = dataproc_v1.CreateBatchRequest(
        parent=f"projects/{project_id}/locations/{region}",
        batch=batch,
        batch_id=batch_id,
    )
    operation = client.create_batch(request=request)
    return {"source_path": source_path, "batch_id": batch_id, "operation": operation.operation.name}
