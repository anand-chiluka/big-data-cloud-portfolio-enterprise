"""
Audit trail logging: records every access to Restricted or
Restricted-Health data, the specific requirement referenced across this
portfolio's SOC 2/HIPAA-adjacent framing (see the b.well and Foodsmart
resume/portfolio context). An audit log that can't answer "who accessed
this record, when, and why" isn't a compliance control, it's a liability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .pii import Classification


@dataclass
class AuditEvent:
    actor: str               # who/what accessed the data (user, service account)
    action: str               # "read" | "write" | "delete" | "export"
    resource: str              # table/collection/file identifier
    record_id: str
    classification: Classification
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: Optional[str] = None   # e.g. a ticket ID, for access to Restricted data
    result: str = "success"         # "success" | "denied"


class AuditLog:
    """In-memory audit log used for testing. In production this would
    write to an append-only, tamper-evident store (a dedicated Snowflake
    table with row-level insert-only grants, or a service like AWS
    CloudTrail / Azure Monitor), never a mutable table the application
    itself can update or delete from.
    """

    def __init__(self):
        self._events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)

    def record_access(self, actor: str, action: str, resource: str, record_id: str,
                       classification: Classification, reason: Optional[str] = None,
                       result: str = "success") -> None:
        self.record(AuditEvent(
            actor=actor, action=action, resource=resource, record_id=record_id,
            classification=classification, reason=reason, result=result,
        ))

    def query(self, actor: Optional[str] = None, classification: Optional[Classification] = None,
               result: Optional[str] = None) -> list[AuditEvent]:
        events = self._events
        if actor is not None:
            events = [e for e in events if e.actor == actor]
        if classification is not None:
            events = [e for e in events if e.classification == classification]
        if result is not None:
            events = [e for e in events if e.result == result]
        return events

    def restricted_access_without_reason(self) -> list[AuditEvent]:
        """Compliance check: any access to Restricted/Restricted-Health
        data that wasn't logged with a reason (e.g. a ticket ID) is
        exactly the kind of finding a SOC 2 or HIPAA audit would flag.
        """
        return [
            e for e in self._events
            if e.classification in (Classification.RESTRICTED, Classification.RESTRICTED_HEALTH)
            and e.reason is None
            and e.result == "success"
        ]
