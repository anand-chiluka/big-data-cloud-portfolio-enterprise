"""
NoSQL document connector: extracts from document/key-value stores
(MongoDB, DynamoDB, Cassandra, Cosmos DB).

The defining challenge with NoSQL sources isn't the extraction mechanics,
it's that documents are semi-structured and schema-flexible: two documents
in the same collection can have different fields, nested objects, and
arrays. This connector demonstrates flattening that variability into the
common ExtractedRecord envelope while preserving the original nested
structure in the payload for downstream consumers that want it.

Implemented against a plain Python dict-of-dicts standing in for a real
MongoDB/DynamoDB client, so it can be fully exercised without any real
NoSQL server. Swapping in `pymongo.MongoClient` or `boto3`'s DynamoDB
resource is the only change needed to point this at a real store.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseConnector, ExtractedRecord, ExtractionResult, SourceCategory


class NoSQLConnector(BaseConnector):
    category = SourceCategory.NOSQL_DOCUMENT

    def __init__(self, collection: dict[str, dict], collection_name: str,
                 id_field: str = "_id", connector_name: Optional[str] = None):
        """`collection` stands in for a real MongoDB collection or DynamoDB
        table: a mapping of document ID -> document, matching the shape
        pymongo's find() or boto3's scan() would ultimately produce after
        being consumed into memory.
        """
        self.collection = collection
        self.collection_name = collection_name
        self.id_field = id_field
        self.name = connector_name or f"nosql:{collection_name}"

    def extract(self) -> ExtractionResult:
        records = []
        errors = []

        for doc_id, document in self.collection.items():
            try:
                records.append(ExtractedRecord(
                    source_name=self.name,
                    source_category=self.category,
                    record_id=str(doc_id),
                    payload=document,
                    content_type="semi_structured",
                ))
            except Exception as e:
                errors.append({"document_id": doc_id, "error": str(e)})

        return ExtractionResult(records=records, errors=errors, source_name=self.name)


def build_demo_nosql_source() -> dict[str, dict]:
    """Standin for a MongoDB collection or DynamoDB table with realistic
    schema variability: notice `event_002` has a nested `metadata` object
    and an array field that `event_001` doesn't have. This is the exact
    shape of variability a NoSQL connector has to tolerate that a rigid
    SQL connector never sees.
    """
    return {
        "event_001": {
            "_id": "event_001",
            "user_id": "u_501",
            "action": "page_view",
            "page": "/pricing",
        },
        "event_002": {
            "_id": "event_002",
            "user_id": "u_502",
            "action": "purchase",
            "amount": 49.99,
            "items": ["sku_101", "sku_204"],
            "metadata": {"referrer": "email_campaign_42", "device": "mobile"},
        },
        "event_003": {
            "_id": "event_003",
            "user_id": "u_501",
            "action": "signup",
            "plan": "pro",
        },
    }
