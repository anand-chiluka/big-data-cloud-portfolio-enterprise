"""
STAR
Situation: Object Storage create events should submit OCI Data Flow runs automatically.
Task: Build an OCI Function that starts a Data Flow application run.
Action: Parse event payload, build object storage path, and call Data Flow using resource principal auth.
Result: Demonstrates OCI serverless orchestration for batch Spark processing.
"""

from __future__ import annotations

import io
import json
import os

import oci
from fdk import response


def handler(ctx, data: io.BytesIO | None = None):
    body = json.loads(data.getvalue()) if data else {}
    bucket = body.get("data", {}).get("additionalDetails", {}).get("bucketName")
    namespace = body.get("data", {}).get("additionalDetails", {}).get("namespace")
    object_name = body.get("data", {}).get("resourceName")
    source_path = f"oci://{bucket}@{namespace}/{object_name}"

    signer = oci.auth.signers.get_resource_principals_signer()
    client = oci.data_flow.DataFlowClient(config={}, signer=signer)
    run_details = oci.data_flow.models.CreateRunDetails(
        application_id=os.environ["DATAFLOW_APPLICATION_ID"],
        compartment_id=os.environ["COMPARTMENT_ID"],
        display_name=f"orders_batch_{object_name.replace('/', '_')[:40]}",
        arguments=["--source", source_path],
    )
    run = client.create_run(run_details).data
    return response.Response(ctx, response_data=json.dumps({"source_path": source_path, "run_id": run.id}))
