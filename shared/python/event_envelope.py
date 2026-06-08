"""
STAR
Situation: Streaming systems need a common event contract across producers and consumers.
Task: Define a small event envelope with traceability, event time, and payload.
Action: Implement serialization helpers and validation in plain Python.
Result: Kafka, Kinesis, Event Hubs, Pub/Sub, and OCI Streaming examples can share event semantics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    event_time: str
    source_system: str
    trace_id: str
    payload: dict[str, Any]

    @staticmethod
    def create(event_type: str, source_system: str, payload: dict[str, Any], trace_id: str | None = None) -> "EventEnvelope":
        now = datetime.now(timezone.utc).isoformat()
        return EventEnvelope(
            event_id=str(uuid4()),
            event_type=event_type,
            event_time=now,
            source_system=source_system,
            trace_id=trace_id or str(uuid4()),
            payload=payload,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


def parse_event(raw: str | bytes) -> EventEnvelope:
    """Parse and validate an event envelope."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    required = {"event_id", "event_type", "event_time", "source_system", "trace_id", "payload"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Event missing required fields: {sorted(missing)}")
    return EventEnvelope(**data)
