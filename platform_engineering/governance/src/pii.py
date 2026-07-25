"""
Data governance utilities: PII detection, field-level masking, and data
classification tagging. Meant to be applied at the connector/sink
boundary across every project in this portfolio, so sensitive data is
classified and protected as a platform-wide default, not an
afterthought bolted onto individual pipelines.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Classification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"      # PII, financial account details
    RESTRICTED_HEALTH = "restricted_health"  # HIPAA-scope health data


# --- PII pattern detection ---
# Deliberately conservative: false positives (flagging something that
# isn't actually PII) are a minor annoyance requiring human review;
# false negatives (missing real PII) are a real compliance and security
# failure. When in doubt, these patterns lean toward flagging.

_PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# Field names that should always be treated as PII regardless of content,
# since the field's meaning alone is enough (e.g. a column literally named
# "date_of_birth" is PII even if a given value looks like plain text).
_PII_FIELD_NAME_HINTS = {
    "ssn", "social_security_number", "date_of_birth", "dob",
    "email", "email_address", "phone", "phone_number",
    "credit_card_number", "card_number", "account_number",
    "passport_number", "drivers_license", "medical_record_number",
}


@dataclass
class PIIFinding:
    field_name: str
    pii_type: str
    detection_method: str  # "pattern_match" | "field_name_hint"


def scan_record_for_pii(record: dict[str, Any]) -> list[PIIFinding]:
    """Scans a single record's fields and values for likely PII.
    Returns every finding; a record can have multiple PII fields.
    """
    findings = []

    for field_name, value in record.items():
        normalized_field = field_name.lower().replace(" ", "_")

        if normalized_field in _PII_FIELD_NAME_HINTS:
            findings.append(PIIFinding(field_name, normalized_field, "field_name_hint"))
            continue

        if not isinstance(value, str):
            continue

        for pii_type, pattern in _PII_PATTERNS.items():
            if pattern.search(value):
                findings.append(PIIFinding(field_name, pii_type, "pattern_match"))
                break  # one finding per field is enough for a scan report

    return findings


def classify_record(record: dict[str, Any], has_health_context: bool = False) -> Classification:
    """Determines the overall classification tier for a record based on
    what PII, if any, it contains. `has_health_context` should be set
    True by the caller when the record comes from a source known to
    contain health data, since HIPAA scope isn't always detectable from
    field names/values alone (e.g. a diagnosis code has no PII pattern
    of its own but is still Restricted-Health in context).
    """
    findings = scan_record_for_pii(record)

    if has_health_context:
        return Classification.RESTRICTED_HEALTH
    if findings:
        return Classification.RESTRICTED
    return Classification.INTERNAL


# --- Masking ---

def _mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    if not domain:
        return "***"
    visible = local[:1] if local else ""
    return f"{visible}***@{domain}"


def _mask_generic(value: str, keep_last: int = 4) -> str:
    if len(value) <= keep_last:
        return "*" * len(value)
    return "*" * (len(value) - keep_last) + value[-keep_last:]


def _hash_value(value: str, salt: str = "") -> str:
    """Irreversible hash, for fields that need to be joinable/comparable
    across records (e.g. deduping by SSN) without ever storing or
    displaying the real value.
    """
    return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()[:16]


def mask_record(record: dict[str, Any], strategy: str = "mask") -> dict[str, Any]:
    """Returns a new record with detected PII fields masked or hashed.
    `strategy` is "mask" (partial redaction, human-readable) or "hash"
    (irreversible, for join keys that must remain comparable).
    """
    findings = {f.field_name for f in scan_record_for_pii(record)}
    masked = dict(record)

    for field_name in findings:
        value = record[field_name]
        if not isinstance(value, str):
            continue

        if strategy == "hash":
            masked[field_name] = _hash_value(value)
        elif "email" in field_name.lower() or _PII_PATTERNS["email"].search(value):
            masked[field_name] = _mask_email(value)
        else:
            masked[field_name] = _mask_generic(value)

    return masked
