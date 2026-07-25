"""
REST API connector: extracts from paginated third-party or internal APIs
(the CRM/SaaS/ERP integration pattern).

Two things make API sources distinct from database sources: pagination
(no API returns everything in one call) and sync semantics (figuring out
what's new, changed, or deleted between this pull and the last one, since
most APIs don't give you a clean changelog for free).

The pagination and sync logic here follows the same created/updated/deleted
reconciliation pattern used for CRM and billing system integrations.
"""

from __future__ import annotations

from typing import Callable, Optional

from .base import BaseConnector, ExtractedRecord, ExtractionResult, SourceCategory


class APIConnector(BaseConnector):
    category = SourceCategory.API_REST

    def __init__(self, fetch_page_fn: Callable[[int], list[dict]], id_field: str = "id",
                 connector_name: str = "api_source", previous_state: Optional[dict[str, dict]] = None):
        """`fetch_page_fn` stands in for a real HTTP client call
        (requests.get(url, params={"page": n})) against a paginated API.
        Swapping it for a real HTTP call is the only change needed to
        point this at a live API.
        """
        self.fetch_page_fn = fetch_page_fn
        self.id_field = id_field
        self.name = connector_name
        self.previous_state = previous_state or {}

    def _fetch_all_pages(self) -> list[dict]:
        all_records = []
        page = 0
        while True:
            page_records = self.fetch_page_fn(page)
            if not page_records:
                break
            all_records.extend(page_records)
            page += 1
        return all_records

    def extract(self) -> ExtractionResult:
        current_records = self._fetch_all_pages()
        current_by_id = {str(r[self.id_field]): r for r in current_records}

        created_ids = current_by_id.keys() - self.previous_state.keys()
        deleted_ids = self.previous_state.keys() - current_by_id.keys()
        common_ids = current_by_id.keys() & self.previous_state.keys()
        updated_ids = {
            rid for rid in common_ids
            if current_by_id[rid] != self.previous_state[rid]
        }

        records = []
        for rid in created_ids | updated_ids:
            change_type = "created" if rid in created_ids else "updated"
            payload = dict(current_by_id[rid])
            payload["_sync_change_type"] = change_type
            records.append(ExtractedRecord(
                source_name=self.name,
                source_category=self.category,
                record_id=rid,
                payload=payload,
                content_type="structured",
            ))

        for rid in deleted_ids:
            records.append(ExtractedRecord(
                source_name=self.name,
                source_category=self.category,
                record_id=rid,
                payload={self.id_field: rid, "_sync_change_type": "deleted"},
                content_type="structured",
            ))

        self.previous_state = current_by_id

        return ExtractionResult(records=records, errors=[], source_name=self.name)


def build_demo_paginated_api(pages: list[list[dict]]) -> Callable[[int], list[dict]]:
    """Turns a plain list of pre-built pages into a callable matching the
    shape of a real paginated API client, so APIConnector can be tested
    without any real HTTP calls.
    """
    def fetch_page(page_number: int) -> list[dict]:
        if page_number < len(pages):
            return pages[page_number]
        return []
    return fetch_page
