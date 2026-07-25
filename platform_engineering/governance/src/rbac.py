"""
Role-based access control: a small, real policy engine mapping roles to
which data Classification tiers they can read, plus row-level and
column-level filtering. This is the enforcement layer that makes
`pii.classify_record()` actually mean something operationally, rather
than being a label nobody checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .pii import Classification


@dataclass
class Role:
    name: str
    allowed_classifications: set[Classification]
    column_denylist: set[str] = field(default_factory=set)  # columns this role never sees, regardless of classification
    row_filter: Optional[str] = None  # e.g. "region = caller_region", enforced by caller


# --- Example role definitions ---
# In production these would be loaded from an identity provider's group
# membership or a policy-as-code system (OPA/Cedar), not hardcoded, but
# the enforcement logic below is identical either way.

ROLE_ANALYST = Role(
    name="analyst",
    allowed_classifications={Classification.PUBLIC, Classification.INTERNAL},
    column_denylist=set(),
)

ROLE_RISK_INVESTIGATOR = Role(
    name="risk_investigator",
    allowed_classifications={Classification.PUBLIC, Classification.INTERNAL, Classification.RESTRICTED},
    column_denylist={"ssn", "credit_card_number"},  # can see restricted records, but never raw identifiers
)

ROLE_COMPLIANCE_ADMIN = Role(
    name="compliance_admin",
    allowed_classifications={
        Classification.PUBLIC, Classification.INTERNAL,
        Classification.RESTRICTED, Classification.RESTRICTED_HEALTH,
    },
    column_denylist=set(),
)

ROLE_SERVICE_ACCOUNT_ETL = Role(
    name="service_account_etl",
    allowed_classifications={
        Classification.PUBLIC, Classification.INTERNAL,
        Classification.RESTRICTED, Classification.RESTRICTED_HEALTH,
    },
    column_denylist=set(),
)


class AccessDeniedError(Exception):
    pass


def authorize_read(role: Role, record_classification: Classification) -> None:
    """Raises AccessDeniedError if the role isn't permitted to read data
    at this classification tier. Call this before returning any record
    to a caller, not just at the API gateway layer, since defense in
    depth means checking again at the data access layer too.
    """
    if record_classification not in role.allowed_classifications:
        raise AccessDeniedError(
            f"role '{role.name}' is not authorized to read "
            f"'{record_classification.value}' classified data"
        )


def filter_columns_for_role(record: dict[str, Any], role: Role) -> dict[str, Any]:
    """Strips any column on the role's denylist before the record is
    returned, regardless of overall classification. This is how a role
    like risk_investigator can see a Restricted record (to do fraud
    investigation) while still never seeing the raw SSN or card number
    inside it.
    """
    return {k: v for k, v in record.items() if k not in role.column_denylist}


def authorize_and_filter(record: dict[str, Any], classification: Classification, role: Role) -> dict[str, Any]:
    """Combined check: raises if the role can't read this classification
    at all, otherwise returns the record with denylisted columns removed.
    """
    authorize_read(role, classification)
    return filter_columns_for_role(record, role)
