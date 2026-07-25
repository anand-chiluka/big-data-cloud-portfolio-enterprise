import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pii import Classification, scan_record_for_pii, classify_record, mask_record
from src.rbac import (
    ROLE_ANALYST, ROLE_RISK_INVESTIGATOR, ROLE_COMPLIANCE_ADMIN,
    AccessDeniedError, authorize_read, filter_columns_for_role, authorize_and_filter,
)
from src.audit import AuditLog


# ---------- PII detection ----------

def test_detects_email_by_pattern():
    record = {"customer_id": "c1", "contact": "jane.doe@example.com"}
    findings = scan_record_for_pii(record)
    assert any(f.pii_type == "email" for f in findings)


def test_detects_ssn_field_by_name_even_without_pattern_match():
    record = {"customer_id": "c1", "ssn": "REDACTED_ALREADY"}
    findings = scan_record_for_pii(record)
    assert any(f.field_name == "ssn" and f.detection_method == "field_name_hint" for f in findings)


def test_clean_record_has_no_findings():
    record = {"customer_id": "c1", "product": "widget", "quantity": 3}
    findings = scan_record_for_pii(record)
    assert findings == []


def test_classify_record_flags_restricted_when_pii_present():
    record = {"customer_id": "c1", "email": "jane@example.com"}
    assert classify_record(record) == Classification.RESTRICTED


def test_classify_record_defaults_to_internal_when_clean():
    record = {"customer_id": "c1", "product": "widget"}
    assert classify_record(record) == Classification.INTERNAL


def test_classify_record_respects_health_context_flag():
    record = {"patient_id": "p1", "diagnosis_code": "E11.9"}
    assert classify_record(record, has_health_context=True) == Classification.RESTRICTED_HEALTH


# ---------- Masking ----------

def test_mask_record_partially_redacts_email():
    record = {"customer_id": "c1", "email": "jane.doe@example.com"}
    masked = mask_record(record)
    assert masked["email"] != record["email"]
    assert masked["email"].endswith("@example.com")
    assert "jane.doe" not in masked["email"]


def test_mask_record_hash_strategy_is_irreversible_and_deterministic():
    record = {"ssn": "123-45-6789"}
    masked_1 = mask_record(record, strategy="hash")
    masked_2 = mask_record(record, strategy="hash")
    assert masked_1["ssn"] == masked_2["ssn"]  # deterministic: same input, same hash
    assert masked_1["ssn"] != record["ssn"]     # but not the original value
    assert len(masked_1["ssn"]) == 16


def test_mask_record_does_not_touch_non_pii_fields():
    record = {"customer_id": "c1", "email": "jane@example.com", "product": "widget"}
    masked = mask_record(record)
    assert masked["product"] == "widget"
    assert masked["customer_id"] == "c1"


# ---------- RBAC ----------

def test_analyst_can_read_internal_data():
    authorize_read(ROLE_ANALYST, Classification.INTERNAL)  # should not raise


def test_analyst_cannot_read_restricted_data():
    try:
        authorize_read(ROLE_ANALYST, Classification.RESTRICTED)
        assert False, "expected AccessDeniedError"
    except AccessDeniedError:
        pass


def test_risk_investigator_can_read_restricted_but_not_raw_ssn_column():
    record = {"customer_id": "c1", "ssn": "123-45-6789", "risk_score": 0.9}
    filtered = authorize_and_filter(record, Classification.RESTRICTED, ROLE_RISK_INVESTIGATOR)
    assert "ssn" not in filtered
    assert filtered["risk_score"] == 0.9


def test_compliance_admin_can_read_restricted_health_data():
    authorize_read(ROLE_COMPLIANCE_ADMIN, Classification.RESTRICTED_HEALTH)  # should not raise


def test_filter_columns_removes_only_denylisted_fields():
    record = {"customer_id": "c1", "ssn": "123-45-6789", "credit_card_number": "4111111111111111"}
    filtered = filter_columns_for_role(record, ROLE_RISK_INVESTIGATOR)
    assert "customer_id" in filtered
    assert "ssn" not in filtered
    assert "credit_card_number" not in filtered


# ---------- Audit logging ----------

def test_audit_log_records_and_queries_events():
    log = AuditLog()
    log.record_access("analyst_jane", "read", "customers_table", "c1",
                       Classification.INTERNAL)
    log.record_access("risk_investigator_bob", "read", "customers_table", "c2",
                       Classification.RESTRICTED, reason="ticket-4521")

    restricted_events = log.query(classification=Classification.RESTRICTED)
    assert len(restricted_events) == 1
    assert restricted_events[0].actor == "risk_investigator_bob"


def test_audit_log_flags_restricted_access_missing_a_reason():
    log = AuditLog()
    log.record_access("service_account_etl", "read", "customers_table", "c1",
                       Classification.RESTRICTED)  # no reason provided -- should be flagged
    log.record_access("risk_investigator_bob", "read", "customers_table", "c2",
                       Classification.RESTRICTED, reason="ticket-4521")  # has a reason -- should not be flagged

    flagged = log.restricted_access_without_reason()
    assert len(flagged) == 1
    assert flagged[0].actor == "service_account_etl"


if __name__ == "__main__":
    test_detects_email_by_pattern()
    test_detects_ssn_field_by_name_even_without_pattern_match()
    test_clean_record_has_no_findings()
    test_classify_record_flags_restricted_when_pii_present()
    test_classify_record_defaults_to_internal_when_clean()
    test_classify_record_respects_health_context_flag()
    test_mask_record_partially_redacts_email()
    test_mask_record_hash_strategy_is_irreversible_and_deterministic()
    test_mask_record_does_not_touch_non_pii_fields()
    test_analyst_can_read_internal_data()
    test_analyst_cannot_read_restricted_data()
    test_risk_investigator_can_read_restricted_but_not_raw_ssn_column()
    test_compliance_admin_can_read_restricted_health_data()
    test_filter_columns_removes_only_denylisted_fields()
    test_audit_log_records_and_queries_events()
    test_audit_log_flags_restricted_access_missing_a_reason()
    print("All tests passed.")
