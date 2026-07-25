"""
Base sink interface. Every cloud sink (Snowflake, AWS, GCP, Azure)
implements `write()` against the same list[ExtractedRecord] input, so the
orchestrator never needs to know which cloud a given pipeline run is
writing to.

Also includes LocalSink, a filesystem-backed implementation used for
testing every connector end-to-end without requiring any real cloud
credentials. Every cloud-specific sink in this package documents itself
honestly: what's real, working Python using the correct SDK calls, versus
what would need real credentials to actually execute.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from ..connectors.base import ExtractedRecord


class BaseSink(ABC):
    name: str

    @abstractmethod
    def write(self, records: list[ExtractedRecord]) -> int:
        """Writes records to the destination, returns count written."""
        raise NotImplementedError


class LocalSink(BaseSink):
    """Writes records as newline-delimited JSON to a local directory.
    Used by every test in this project so the full connector -> sink
    path can be exercised without any cloud account.
    """

    def __init__(self, output_dir: str, name: str = "local_sink"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.name = name

    def write(self, records: list[ExtractedRecord]) -> int:
        if not records:
            return 0

        by_source: dict[str, list[ExtractedRecord]] = {}
        for r in records:
            by_source.setdefault(r.source_name, []).append(r)

        for source_name, source_records in by_source.items():
            safe_name = source_name.replace(":", "_").replace("/", "_")
            out_path = self.output_dir / f"{safe_name}.ndjson"
            with open(out_path, "a", encoding="utf-8") as f:
                for r in source_records:
                    f.write(json.dumps({
                        "record_id": r.record_id,
                        "source_name": r.source_name,
                        "source_category": r.source_category.value,
                        "content_type": r.content_type,
                        "extracted_at": r.extracted_at,
                        "payload": r.payload,
                    }, default=str) + "\n")

        return len(records)
