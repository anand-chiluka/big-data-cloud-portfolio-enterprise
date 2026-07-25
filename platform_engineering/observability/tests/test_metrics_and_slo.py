import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.metrics import MetricsRegistry
from src.slo import SLO_DEFINITIONS, check_slo, check_all_slos


def test_counter_accumulates_correctly():
    metrics = MetricsRegistry(namespace="test")
    metrics.increment("records_extracted", 10)
    metrics.increment("records_extracted", 5)
    assert metrics.sum("records_extracted") == 15


def test_gauge_tracks_latest_value():
    metrics = MetricsRegistry(namespace="test")
    metrics.gauge("queue_depth", 100)
    metrics.gauge("queue_depth", 42)
    assert metrics.latest_gauge("queue_depth") == 42


def test_timer_records_positive_duration():
    metrics = MetricsRegistry(namespace="test")
    with metrics.timer("extract_duration_seconds"):
        time.sleep(0.01)
    points = metrics.get_points("extract_duration_seconds")
    assert len(points) == 1
    assert points[0].value > 0
    assert points[0].metric_type == "histogram"


def test_summary_produces_correct_aggregates():
    metrics = MetricsRegistry(namespace="test")
    metrics.increment("records_extracted", 10)
    metrics.increment("records_extracted", 20)
    summary = metrics.summary()
    key = "test.records_extracted"
    assert summary[key]["count"] == 2
    assert summary[key]["sum"] == 30
    assert summary[key]["avg"] == 15


def test_slo_passes_when_within_threshold():
    metrics = MetricsRegistry(namespace="test")
    metrics.observe("extract_duration_seconds", 12.0)
    slo = next(s for s in SLO_DEFINITIONS if s.name == "extraction_latency")
    result = check_slo(slo, metrics)
    assert result.passed is True
    assert result.actual_value == 12.0


def test_slo_fails_when_threshold_exceeded():
    metrics = MetricsRegistry(namespace="test")
    metrics.observe("extract_duration_seconds", 45.0)
    slo = next(s for s in SLO_DEFINITIONS if s.name == "extraction_latency")
    result = check_slo(slo, metrics)
    assert result.passed is False
    assert result.actual_value == 45.0


def test_slo_fails_when_no_data_available():
    metrics = MetricsRegistry(namespace="test")
    slo = next(s for s in SLO_DEFINITIONS if s.name == "extraction_latency")
    result = check_slo(slo, metrics)
    assert result.passed is False
    assert result.actual_value is None


def test_check_all_slos_returns_one_result_per_definition():
    metrics = MetricsRegistry(namespace="test")
    results = check_all_slos(metrics)
    assert len(results) == len(SLO_DEFINITIONS)


if __name__ == "__main__":
    test_counter_accumulates_correctly()
    test_gauge_tracks_latest_value()
    test_timer_records_positive_duration()
    test_summary_produces_correct_aggregates()
    test_slo_passes_when_within_threshold()
    test_slo_fails_when_threshold_exceeded()
    test_slo_fails_when_no_data_available()
    test_check_all_slos_returns_one_result_per_definition()
    print("All tests passed.")
