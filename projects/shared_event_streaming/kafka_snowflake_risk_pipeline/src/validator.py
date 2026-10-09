"""
STAR
Situation: Streaming pipelines fail late and silently when malformed events reach the warehouse.
Task: Reject bad events at the front door with a specific, machine-readable reason.
Action: Parse the shared event envelope, then validate the payment_attempt payload contract field by field.
Result: Every bad event is routed to a dead-letter record with a reason code instead of corrupting downstream tables.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

ENVELOPE_FIELDS = {"event_id", "event_type", "event_time", "source_system", "trace_id", "payload"}
PAYLOAD_TYPES: dict[str, tuple[type, ...]] = {
    "account_id": (str,),
    "merchant_id": (str,),
    "device_id": (str,),
    "country": (str,),
    "currency": (str,),
    "amount": (int, float),
}
SUPPORTED_EVENT_TYPES = {"payment_attempt"}


class ValidationError(ValueError):
    """Raised with a stable reason code so DLQ records can be grouped and counted."""

    def __init__(self, reason_code: str, detail: str) -> None:
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


@dataclass(frozen=True)
class RiskEvent:
    event_id: str
    event_time: datetime
    source_system: str
    trace_id: str
    account_id: str
    merchant_id: str
    device_id: str
    country: str
    currency: str
    amount: float


def parse_and_validate(raw: str | bytes) -> RiskEvent:
    """Parse a raw Kafka message value into a validated RiskEvent or raise ValidationError."""
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("malformed_json", str(exc)) from exc
    if not isinstance(data, dict):
        raise ValidationError("malformed_json", "top-level value is not an object")

    missing = ENVELOPE_FIELDS - set(data)
    if missing:
        raise ValidationError("missing_envelope_fields", str(sorted(missing)))
    if data["event_type"] not in SUPPORTED_EVENT_TYPES:
        raise ValidationError("unsupported_event_type", str(data["event_type"]))

    try:
        event_time = datetime.fromisoformat(str(data["event_time"]))
    except ValueError as exc:
        raise ValidationError("bad_event_time", str(data["event_time"])) from exc
    if event_time.tzinfo is None:
        raise ValidationError("bad_event_time", "timestamp must be timezone-aware")

    payload: Any = data["payload"]
    if not isinstance(payload, dict):
        raise ValidationError("bad_payload", "payload is not an object")
    for name, types in PAYLOAD_TYPES.items():
        if name not in payload or payload[name] in (None, ""):
            raise ValidationError("missing_payload_field", name)
        value = payload[name]
        if isinstance(value, bool) or not isinstance(value, types):
            raise ValidationError("wrong_payload_type", f"{name}={value!r}")
    if payload["amount"] <= 0:
        raise ValidationError("amount_not_positive", str(payload["amount"]))

    return RiskEvent(
        event_id=str(data["event_id"]),
        event_time=event_time,
        source_system=str(data["source_system"]),
        trace_id=str(data["trace_id"]),
        account_id=payload["account_id"],
        merchant_id=payload["merchant_id"],
        device_id=payload["device_id"],
        country=payload["country"],
        currency=payload["currency"],
        amount=float(payload["amount"]),
    )
