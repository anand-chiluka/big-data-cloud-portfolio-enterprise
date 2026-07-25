"""
Batch file connector: extracts from CSV, JSON, and Parquet files landing
in a directory (the classic "nightly file drop" or "vendor SFTP export"
pattern that predates and still coexists alongside real-time sources).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from .base import BaseConnector, ExtractedRecord, ExtractionResult, SourceCategory


class BatchFileConnector(BaseConnector):
    category = SourceCategory.BATCH_FILE

    def __init__(self, directory: str, id_field: str = "id",
                 connector_name: str = "batch_files"):
        self.directory = Path(directory)
        self.id_field = id_field
        self.name = connector_name

    def _read_csv(self, path: Path) -> list[dict]:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _read_json(self, path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]

    def _read_parquet(self, path: Path) -> list[dict]:
        import pyarrow.parquet as pq
        table = pq.read_table(str(path))
        return table.to_pylist()

    def extract(self) -> ExtractionResult:
        records = []
        errors = []

        if not self.directory.exists():
            return ExtractionResult(records=[], errors=[{"error": "directory_not_found"}], source_name=self.name)

        for file_path in sorted(self.directory.iterdir()):
            try:
                if file_path.suffix == ".csv":
                    rows = self._read_csv(file_path)
                elif file_path.suffix == ".json":
                    rows = self._read_json(file_path)
                elif file_path.suffix == ".parquet":
                    rows = self._read_parquet(file_path)
                else:
                    continue

                for i, row in enumerate(rows):
                    record_id = str(row.get(self.id_field, f"{file_path.stem}_{i}"))
                    records.append(ExtractedRecord(
                        source_name=self.name,
                        source_category=self.category,
                        record_id=record_id,
                        payload=row,
                        content_type="structured",
                    ))

            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})

        return ExtractionResult(records=records, errors=errors, source_name=self.name)
