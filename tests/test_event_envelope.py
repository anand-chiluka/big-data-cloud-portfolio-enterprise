from shared.python.event_envelope import EventEnvelope, parse_event


def test_event_envelope_round_trip():
    event = EventEnvelope.create("order_created", "pytest", {"order_id": "1"})
    parsed = parse_event(event.to_json())
    assert parsed.event_id == event.event_id
    assert parsed.payload["order_id"] == "1"
