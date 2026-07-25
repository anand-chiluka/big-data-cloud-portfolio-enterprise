"""
Azure sink: writes records to Azure Data Lake Storage Gen2, the standard
landing pattern that Synapse's COPY INTO or an ADF pipeline would then
load from.

HONESTY NOTE: uses the real azure-storage-file-datalake SDK API correctly.
NOT executed against a real Azure account in this environment, since no
Azure credentials are available here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .base import BaseSink
from ..connectors.base import ExtractedRecord


class AzureSink(BaseSink):
    def __init__(self, account_url: str, filesystem: str, directory: str = "raw",
                 name: str = "adls_sink"):
        self.account_url = account_url
        self.filesystem = filesystem
        self.directory = directory
        self.name = name

    def _build_path(self) -> str:
        now = datetime.now(timezone.utc)
        return f"{self.directory}/year={now.year}/month={now.month:02d}/day={now.day:02d}/{now.strftime('%Y%m%dT%H%M%S')}.ndjson"

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

        # Production code path (requires: pip install azure-storage-file-datalake,
        # real Azure credentials via DefaultAzureCredential or a connection string)
        #
        # from azure.storage.filedatalake import DataLakeServiceClient
        # from azure.identity import DefaultAzureCredential
        #
        # service_client = DataLakeServiceClient(
        #     account_url=self.account_url, credential=DefaultAzureCredential()
        # )
        # fs_client = service_client.get_file_system_client(self.filesystem)
        # file_client = fs_client.create_file(self._build_path())
        # file_client.append_data(data=body, offset=0, length=len(body))
        # file_client.flush_data(len(body))
        # return len(records)

        raise NotImplementedError(
            "AzureSink.write() requires real Azure credentials and "
            "azure-storage-file-datalake. The production code path (ADLS "
            "Gen2 file append) is documented in comments above this line."
        )
