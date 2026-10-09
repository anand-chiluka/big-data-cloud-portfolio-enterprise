"""
STAR
Situation: Kafka delivers at least once, so the same event can arrive twice after a retry or rebalance.
Task: Make writes safe to repeat without double counting.
Action: Key every write on event_id; Snowflake uses MERGE ... WHEN NOT MATCHED, and the in-memory sink applies the same rule for tests.
Result: Replaying a batch any number of times leaves the table unchanged after the first successful write.
"""

from __future__ import annotations

import json
from typing import Protocol

from src.enrichment import EnrichedEvent

MERGE_SQL = """
MERGE INTO RISK_SIGNALS AS t
USING (SELECT %(event_id)s AS event_id) AS s
ON t.event_id = s.event_id
WHEN NOT MATCHED THEN INSERT
  (event_id, event_time, account_id, merchant_id, device_id, country, currency, amount,
   tx_count_5m, amount_sum_5m, distinct_countries_1h, is_new_device, risk_flags, risk_score)
VALUES
  (%(event_id)s, %(event_time)s, %(account_id)s, %(merchant_id)s, %(device_id)s, %(country)s,
   %(currency)s, %(amount)s, %(tx_count_5m)s, %(amount_sum_5m)s, %(distinct_countries_1h)s,
   %(is_new_device)s, %(risk_flags)s, %(risk_score)s)
"""


def to_row(item: EnrichedEvent) -> dict:
    e = item.event
    return {
        "event_id": e.event_id,
        "event_time": e.event_time.isoformat(),
        "account_id": e.account_id,
        "merchant_id": e.merchant_id,
        "device_id": e.device_id,
        "country": e.country,
        "currency": e.currency,
        "amount": e.amount,
        "tx_count_5m": item.tx_count_5m,
        "amount_sum_5m": item.amount_sum_5m,
        "distinct_countries_1h": item.distinct_countries_1h,
        "is_new_device": item.is_new_device,
        "risk_flags": json.dumps(list(item.risk_flags)),
        "risk_score": item.risk_score,
    }


class Sink(Protocol):
    def write(self, rows: list[EnrichedEvent]) -> int:
        """Write rows idempotently and return how many were newly inserted."""


class InMemorySink:
    """Test double with the same semantics as the Snowflake MERGE: first write per event_id wins."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def write(self, rows: list[EnrichedEvent]) -> int:
        inserted = 0
        for item in rows:
            if item.event.event_id not in self.rows:
                self.rows[item.event.event_id] = to_row(item)
                inserted += 1
        return inserted


class SnowflakeMergeSink:
    """Takes an open snowflake-connector connection. Not exercised against a live account in this repo."""

    def __init__(self, connection) -> None:
        self._conn = connection

    def write(self, rows: list[EnrichedEvent]) -> int:
        cursor = self._conn.cursor()
        inserted = 0
        try:
            for item in rows:
                cursor.execute(MERGE_SQL, to_row(item))
                inserted += max(cursor.rowcount or 0, 0)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()
        return inserted
