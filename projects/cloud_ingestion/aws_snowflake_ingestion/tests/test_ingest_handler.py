import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

from ingest_handler import validate_events, events_to_parquet_bytes, build_s3_key
import pyarrow.parquet as pq
import io


def test_valid_events_pass_validation():
    events = [
        {"event_id": "e1", "account_id": "a1", "amount": 10.0,
         "currency": "USD", "event_ts": "2026-01-01T00:00:00Z"},
    ]
    result = validate_events(events)
    assert len(result.valid_events) == 1
    assert len(result.rejected_events) == 0


def test_missing_required_field_is_rejected():
    events = [{"event_id": "e1", "account_id": "a1"}]  # missing amount, currency, event_ts
    result = validate_events(events)
    assert len(result.valid_events) == 0
    assert len(result.rejected_events) == 1
    assert "missing_fields" in result.rejected_events[0]["reason"]


def test_non_numeric_amount_is_rejected():
    events = [
        {"event_id": "e1", "account_id": "a1", "amount": "not_a_number",
         "currency": "USD", "event_ts": "2026-01-01T00:00:00Z"},
    ]
    result = validate_events(events)
    assert len(result.valid_events) == 0
    assert result.rejected_events[0]["reason"] == "amount_not_numeric"


def test_parquet_conversion_round_trips_correctly():
    events = [
        {"event_id": "e1", "account_id": "a1", "amount": 10.0,
         "currency": "USD", "event_ts": "2026-01-01T00:00:00Z"},
        {"event_id": "e2", "account_id": "a2", "amount": 20.0,
         "currency": "USD", "event_ts": "2026-01-01T00:01:00Z"},
    ]
    parquet_bytes = events_to_parquet_bytes(events)
    table = pq.read_table(io.BytesIO(parquet_bytes))
    assert table.num_rows == 2
    assert set(table.column_names) == {"event_id", "account_id", "amount", "currency", "event_ts"}


def test_s3_key_is_correctly_partitioned_by_date():
    key = build_s3_key()
    assert key.startswith("raw/transaction_events/year=")
    assert "/month=" in key
    assert "/day=" in key
    assert key.endswith(".parquet")


if __name__ == "__main__":
    test_valid_events_pass_validation()
    test_missing_required_field_is_rejected()
    test_non_numeric_amount_is_rejected()
    test_parquet_conversion_round_trips_correctly()
    test_s3_key_is_correctly_partitioned_by_date()
    print("All tests passed.")
