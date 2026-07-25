"""
Base connector interface.

Every source connector (SQL, NoSQL, API, unstructured, batch file, Kafka)
implements this same interface, so the orchestrator and any sink can work
with any source uniformly. This mirrors how real ingestion platforms
(Airbyte, Fivetran) are architected: a common contract between wildly
different source types, so adding a new source never requires changing
downstream code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator, Optional


class SourceCategory(str, Enum):
    STRUCTURED_SQL = "structured_sql"
    NOSQL_DOCUMENT = "nosql_document"
    API_REST = "api_rest"
    UNSTRUCTURED = "unstructured"
    BATCH_FILE = "batch_file"
    STREAMING = "streaming"


@dataclass
class ExtractedRecord:
    """A single record from any source, normalized into a common envelope.

    Keeping the envelope identical across source types is what lets a
    single sink implementation (e.g. SnowflakeSink) accept records from
    a SQL table, a MongoDB collection, a REST API, or a PDF chunk without
    needing source-specific branching logic.
    """
    source_name: str
    source_category: SourceCategory
    record_id: str
    payload: dict[str, Any]
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_type: str = "structured"  # "structured" | "semi_structured" | "unstructured"


@dataclass
class ExtractionResult:
    records: list[ExtractedRecord]
    errors: list[dict]
    source_name: str

    @property
    def success_count(self) -> int:
        return len(self.records)

    @property
    def error_count(self) -> int:
        return len(self.errors)


class BaseConnector(ABC):
    """Every connector implements `extract()`. Connectors that support
    incremental extraction also implement `get_cursor()`/`set_cursor()`
    so the orchestrator can resume from the last successful point rather
    than re-extracting everything on every run.
    """

    category: SourceCategory
    name: str

    @abstractmethod
    def extract(self) -> ExtractionResult:
        """Pulls records from the source and returns them in the common
        ExtractedRecord envelope, along with any per-record errors.
        """
        raise NotImplementedError

    def get_cursor(self) -> Optional[str]:
        """Override in connectors that support incremental extraction
        (e.g. a SQL connector tracking a high-water-mark timestamp, or an
        API connector tracking a pagination token). Returns None for
        connectors that only support full extraction.
        """
        return None

    def set_cursor(self, cursor: str) -> None:
        """Restores extraction state from a previous run's cursor."""
        pass
