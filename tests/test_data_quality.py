from shared.python.data_quality import duplicate_keys, require_fields, require_numeric_range


def test_require_fields_passes_for_complete_records():
    result = require_fields([{"id": "1", "amount": 10}], ["id", "amount"])
    assert result.passed is True


def test_duplicate_keys_detects_duplicates():
    result = duplicate_keys([{"id": "1"}, {"id": "1"}, {"id": "2"}], "id")
    assert result.passed is False
    assert result.failed_count == 1


def test_numeric_range_detects_bad_values():
    result = require_numeric_range([{"amount": "5"}, {"amount": "5000"}], "amount", 0, 1000)
    assert result.passed is False
