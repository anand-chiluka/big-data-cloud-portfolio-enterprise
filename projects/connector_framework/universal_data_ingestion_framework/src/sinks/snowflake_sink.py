"""
Snowflake sink: batches ExtractedRecords and writes them via a staged
PUT + COPY INTO, the standard high-throughput pattern for loading batches
of records into Snowflake (much faster than row-by-row INSERT for
anything beyond trivial volume).

HONESTY NOTE: The `write()` method below uses the real
`snowflake-connector-python` API surface correctly (cursor.execute,
PUT, COPY INTO). It has NOT been run against a live Snowflake account in
this environment, since no real account credentials are available here.
It has been reviewed for correct API usage but not executed end-to-end.
See `dbt_snowflake_subscriptions/` and `aws_snowflake_ingestion/` in this
repo for the projects where the Snowflake-adjacent logic (dbt models,
Snowpipe SQL) WAS validated with real tooling (`dbt parse`/`dbt compile`).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .base import BaseSink
from ..connectors.base import ExtractedRecord


class SnowflakeSink(BaseSink):
    def __init__(self, account: str, user: str, password: str, warehouse: str,
                 database: str, schema: str, table: str, name: str = "snowflake_sink"):
        self.account = account
        self.user = user
        self.password = password
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.table = table
        self.name = name

    def write(self, records: list[ExtractedRecord]) -> int:
        if not records:
            return 0

        # Production code path (requires: pip install snowflake-connector-python)
        #
        # import snowflake.connector
        # conn = snowflake.connector.connect(
        #     account=self.account, user=self.user, password=self.password,
        #     warehouse=self.warehouse, database=self.database, schema=self.schema,
        # )
        # cur = conn.cursor()
        #
        # with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        #     for r in records:
        #         f.write(json.dumps({
        #             "record_id": r.record_id, "source_name": r.source_name,
        #             "content_type": r.content_type, "extracted_at": r.extracted_at,
        #             "payload": r.payload,
        #         }, default=str) + "\n")
        #     staged_file = f.name
        #
        # cur.execute(f"PUT file://{staged_file} @%{self.table}")
        # cur.execute(f"""
        #     COPY INTO {self.database}.{self.schema}.{self.table}
        #     FILE_FORMAT = (TYPE = 'JSON')
        #     ON_ERROR = 'SKIP_FILE_10%'
        # """)
        # conn.close()
        # return len(records)

        raise NotImplementedError(
            "SnowflakeSink.write() requires a real Snowflake account and the "
            "snowflake-connector-python package. The production code path is "
            "documented in comments above this line. For local testing, use "
            "sinks.base.LocalSink instead, which every test in this project uses."
        )
