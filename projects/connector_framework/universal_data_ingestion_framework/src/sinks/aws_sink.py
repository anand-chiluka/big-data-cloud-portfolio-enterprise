"""
AWS sink: writes records to S3 as newline-delimited JSON, the standard
landing format Redshift's COPY command or a downstream Snowpipe/Glue
crawler would pick up.

HONESTY NOTE: uses the real boto3 S3 client API correctly. NOT executed
against a real AWS account in this environment, since no AWS credentials
are available here. The Lambda ingestion logic in
`aws_snowflake_ingestion/lambda/ingest_handler.py` in this repo IS
actually tested and run locally; this sink follows the same S3 write
pattern documented there.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .base import BaseSink
from ..connectors.base import ExtractedRecord


class AWSSink(BaseSink):
    def __init__(self, bucket: str, prefix: str = "raw", region: str = "us-west-2",
                 name: str = "aws_s3_sink"):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self.name = name

    def _build_key(self) -> str:
        now = datetime.now(timezone.utc)
        return f"{self.prefix}/year={now.year}/month={now.month:02d}/day={now.day:02d}/{now.strftime('%Y%m%dT%H%M%S')}.ndjson"

    def write(self, records: list[ExtractedRecord]) -> int:
        if not records:
            return 0

        body = "\n".join(
            json.dumps({
                "record_id": r.record_id, "source_name": r.source_name,
                "source_category": r.source_category.value, "content_type": r.content_type,
                "extracted_at": r.extracted_at, "payload": r.payload,
            }, default=str)
            for r in records
        )

        # Production code path (requires: pip install boto3, real AWS credentials)
        #
        # import boto3
        # s3 = boto3.client("s3", region_name=self.region)
        # key = self._build_key()
        # s3.put_object(Bucket=self.bucket, Key=key, Body=body.encode("utf-8"))
        # return len(records)

        raise NotImplementedError(
            "AWSSink.write() requires real AWS credentials and boto3. The "
            "production code path is documented in comments above. For a "
            "fully tested equivalent, see aws_snowflake_ingestion/lambda/"
            "ingest_handler.py in this repo, which IS run and tested locally "
            "against a filesystem stand-in for S3."
        )
