import json
from datetime import datetime, timedelta, timezone

import pytest

from src.consumer import main  # noqa: F401  (import must work without a broker)
from src.enrichment import FeatureEnricher
from src.pipeline import RiskPipeline
from src.sink import InMemorySink
from src.validator import ValidationError, parse_and_validate

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def msg(i=1, minutes=0, account="acc1", device="dev1", country="US", amount=50.0, **over):
    body = {
        "event_id": f"evt{i}",
        "event_type": "payment_attempt",
        "event_time": (T0 + timedelta(minutes=minutes)).isoformat(),
        "source_system": "test",
        "trace_id": f"trace{i}",
        "payload": {
            "account_id": account, "merchant_id": "m1", "device_id": device,
            "country": country, "currency": "USD", "amount": amount,
        },
    }
    body.update(over)
    return json.dumps(body)


# ---- validation ----
def test_valid_event_parses():
    assert parse_and_validate(msg()).account_id == "acc1"


@pytest.mark.parametrize("raw,code", [
    ("not json", "malformed_json"),
    ("[1]", "malformed_json"),
    (json.dumps({"event_id": "x"}), "missing_envelope_fields"),
    (msg(event_type="refund"), "unsupported_event_type"),
    (msg(event_time="yesterday"), "bad_event_time"),
    (msg(event_time="2026-01-01T12:00:00"), "bad_event_time"),
    (msg(amount=-5), "amount_not_positive"),
    (msg(amount="12"), "wrong_payload_type"),
    (msg(payload={"account_id": "a"}), "missing_payload_field"),
])
def test_invalid_events_have_reason_codes(raw, code):
    with pytest.raises(ValidationError) as exc:
        parse_and_validate(raw)
    assert exc.value.reason_code == code


# ---- enrichment ----
def test_velocity_flag_after_five_in_five_minutes():
    enricher = FeatureEnricher()
    last = None
    for i in range(5):
        last = enricher.enrich(parse_and_validate(msg(i, minutes=i)))
    assert last.tx_count_5m == 5 and "high_velocity" in last.risk_flags


def test_window_evicts_old_events():
    enricher = FeatureEnricher()
    enricher.enrich(parse_and_validate(msg(1, minutes=0)))
    later = enricher.enrich(parse_and_validate(msg(2, minutes=90)))
    assert later.tx_count_5m == 1 and later.distinct_countries_1h == 1


def test_new_device_and_country_hopping():
    enricher = FeatureEnricher()
    enricher.enrich(parse_and_validate(msg(1, minutes=0, country="US")))
    enricher.enrich(parse_and_validate(msg(2, minutes=1, country="GB")))
    out = enricher.enrich(parse_and_validate(msg(3, minutes=2, country="JP", device="dev2")))
    assert {"country_hopping", "new_device"} <= set(out.risk_flags)


def test_first_event_is_not_a_new_device():
    assert not FeatureEnricher().enrich(parse_and_validate(msg())).is_new_device


def test_accounts_do_not_share_state():
    enricher = FeatureEnricher()
    for i in range(4):
        enricher.enrich(parse_and_validate(msg(i, minutes=i, account="a")))
    assert enricher.enrich(parse_and_validate(msg(9, minutes=5, account="b"))).tx_count_5m == 1


# ---- pipeline, dead letters, idempotency ----
def test_good_and_bad_events_are_routed():
    sink = InMemorySink()
    result = RiskPipeline(sink).process_batch([msg(1), "garbage", msg(2, amount=-1)])
    assert result.written == 1 and len(sink.rows) == 1
    assert [d.reason_code for d in result.dead_letters] == ["malformed_json", "amount_not_positive"]
    assert result.committable


def test_replay_is_idempotent():
    sink = InMemorySink()
    batch = [msg(1), msg(2, minutes=1)]
    first = RiskPipeline(sink).process_batch(batch)
    again = RiskPipeline(sink).process_batch(batch)
    assert first.written == 2 and again.written == 0 and again.duplicates == 2
    assert len(sink.rows) == 2


def test_sink_failure_blocks_commit():
    class Boom:
        def write(self, rows):
            raise RuntimeError("warehouse down")

    result = RiskPipeline(Boom()).process_batch([msg(1)])
    assert not result.committable
    assert result.dead_letters[-1].reason_code == "sink_failure"


def test_high_score_stored_with_flags():
    sink = InMemorySink()
    batch = [msg(i, minutes=i) for i in range(5)] + [msg(9, minutes=5, amount=2000)]
    RiskPipeline(sink).process_batch(batch)
    row = sink.rows["evt9"]
    assert row["risk_score"] >= 40 and "high_amount" in json.loads(row["risk_flags"])
