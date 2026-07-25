"""
Observability library: structured logging + Prometheus-style metrics
emitter, meant to be imported by every connector and sink across the
portfolio rather than reimplemented per-project.

Design principle: instrumentation should be nearly invisible at the call
site. A connector author writes `metrics.increment("records_extracted", n)`
and doesn't need to know or care whether that metric ends up in
CloudWatch, Prometheus, Datadog, or a local dict during tests, the
MetricsRegistry abstraction below handles that.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional


# ---------------------------------------------------------------------------
# Structured logging: every log line is a JSON object, not free text, so
# it's queryable in CloudWatch Logs Insights / Datadog Log Explorer /
# Snowflake external tables without regex parsing.
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Anything passed via `extra={...}` in a log call rides along here,
        # e.g. log.info("extracted", extra={"source": "sql", "count": 42})
        for key, value in record.__dict__.items():
            if key not in payload and key not in (
                "args", "msg", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name",
            ):
                payload[key] = value
        return json.dumps(payload, default=str)


def get_structured_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------------------------------------------------------------------------
# Metrics: counters, gauges, histograms. In-memory registry by default
# (used by every test in this repo); swap `emit()` for a real
# statsd/Prometheus pushgateway/CloudWatch PutMetricData call in production.
# ---------------------------------------------------------------------------

@dataclass
class MetricPoint:
    name: str
    value: float
    metric_type: str  # "counter" | "gauge" | "histogram"
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetricsRegistry:
    """In-memory metrics registry. Every value emitted is retained so
    tests can assert on exact metric values, and so `summary()` can
    produce a quick health snapshot without a real metrics backend.
    """

    def __init__(self, namespace: str = "data_platform"):
        self.namespace = namespace
        self._points: list[MetricPoint] = []
        self._gauges: dict[str, float] = {}
        self.log = get_structured_logger(f"metrics.{namespace}")

    def increment(self, name: str, value: float = 1, labels: Optional[dict[str, str]] = None) -> None:
        self._emit(name, value, "counter", labels or {})

    def gauge(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        labels = labels or {}
        key = f"{name}:{labels}"
        self._gauges[key] = value
        self._emit(name, value, "gauge", labels)

    def observe(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Records a histogram observation, e.g. a pipeline run's duration
        in seconds or a batch's record count.
        """
        self._emit(name, value, "histogram", labels or {})

    @contextmanager
    def timer(self, name: str, labels: Optional[dict[str, str]] = None) -> Iterator[None]:
        """Context manager measuring wall-clock duration of the wrapped
        block and recording it as a histogram observation in seconds.
        Usage: `with metrics.timer("extract_duration_seconds"): ...`
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.observe(name, elapsed, labels)

    def _emit(self, name: str, value: float, metric_type: str, labels: dict[str, str]) -> None:
        full_name = f"{self.namespace}.{name}"
        point = MetricPoint(name=full_name, value=value, metric_type=metric_type, labels=labels)
        self._points.append(point)

        # Production path: swap this log line for a real emit call, e.g.
        #   statsd_client.incr(full_name, value, tags=[f"{k}:{v}" for k,v in labels.items()])
        # or CloudWatch:
        #   cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=[{
        #       "MetricName": name, "Value": value, "Dimensions": [...]
        #   }])
        self.log.info(
            "metric_emitted",
            extra={"metric_name": full_name, "value": value, "type": metric_type, "labels": labels},
        )

    def get_points(self, name: Optional[str] = None) -> list[MetricPoint]:
        if name is None:
            return list(self._points)
        full_name = f"{self.namespace}.{name}"
        return [p for p in self._points if p.name == full_name]

    def sum(self, name: str) -> float:
        return sum(p.value for p in self.get_points(name))

    def latest_gauge(self, name: str, labels: Optional[dict[str, str]] = None) -> Optional[float]:
        key = f"{name}:{labels or {}}"
        return self._gauges.get(key)

    def summary(self) -> dict[str, Any]:
        """A quick health snapshot: total count and sum per metric name,
        the kind of thing an on-call engineer wants at a glance without
        querying a real dashboard.
        """
        by_name: dict[str, list[float]] = defaultdict(list)
        for p in self._points:
            by_name[p.name].append(p.value)

        return {
            name: {"count": len(values), "sum": sum(values), "avg": sum(values) / len(values)}
            for name, values in by_name.items()
        }
