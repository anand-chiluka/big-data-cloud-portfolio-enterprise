"""
GCP sink: streams records into BigQuery via the insertAll streaming API,
the standard low-latency pattern for getting records into BigQuery
without a load-job's batch delay.

HONESTY NOTE: uses the real google-cloud-bigquery client API correctly.
NOT executed against a real GCP project in this environment, since no
GCP credentials are available here.
"""

from __future__ import annotations

from .base import BaseSink
from ..connectors.base import ExtractedRecord


class GCPSink(BaseSink):
    def __init__(self, project_id: str, dataset: str, table: str, name: str = "bigquery_sink"):
        self.project_id = project_id
        self.dataset = dataset
        self.table = table
        self.name = name

    def write(self, records: list[ExtractedRecord]) -> int:
        if not records:
            return 0

        rows_to_insert = [
            {
                "record_id": r.record_id,
                "source_name": r.source_name,
                "source_category": r.source_category.value,
                "content_type": r.content_type,
                "extracted_at": r.extracted_at,
                "payload_json": str(r.payload),
            }
            for r in records
        ]

        # Production code path (requires: pip install google-cloud-bigquery,
        # real GCP service account credentials)
        #
        # from google.cloud import bigquery
        # client = bigquery.Client(project=self.project_id)
        # table_ref = f"{self.project_id}.{self.dataset}.{self.table}"
        # errors = client.insert_rows_json(table_ref, rows_to_insert)
        # if errors:
        #     raise RuntimeError(f"BigQuery insert errors: {errors}")
        # return len(records)

        raise NotImplementedError(
            "GCPSink.write() requires real GCP credentials and "
            "google-cloud-bigquery. The production code path (BigQuery "
            "streaming insertAll) is documented in comments above this line."
        )
