"""
STAR
Situation: Consumer wiring is hard to test when business logic is tangled with Kafka calls.
Task: Keep validate, enrich, gate, and write in one pure, testable unit.
Action: Process a batch of raw messages, route failures to dead-letter records, and report which messages are safe to commit.
Result: Offsets are committed only for messages whose outcome is durable (written or dead-lettered), so a failed sink write is retried.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src import quality_gate
from src.enrichment import EnrichedEvent, FeatureEnricher
from src.sink import Sink
from src.validator import ValidationError, parse_and_validate


@dataclass
class DeadLetter:
    raw: str
    reason_code: str
    detail: str
    stage: str


@dataclass
class BatchResult:
    written: int = 0
    duplicates: int = 0
    dead_letters: list[DeadLetter] = field(default_factory=list)
    committable: bool = True


class RiskPipeline:
    def __init__(self, sink: Sink, enricher: FeatureEnricher | None = None) -> None:
        self._sink = sink
        self._enricher = enricher or FeatureEnricher()

    def process_batch(self, messages: list[str | bytes]) -> BatchResult:
        result = BatchResult()
        good: list[EnrichedEvent] = []
        for raw in messages:
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            try:
                event = parse_and_validate(raw)
            except ValidationError as exc:
                result.dead_letters.append(DeadLetter(text, exc.reason_code, exc.detail, "validation"))
                continue
            enriched = self._enricher.enrich(event)
            gate = quality_gate.check(enriched)
            if not gate.passed:
                result.dead_letters.append(DeadLetter(text, gate.reason_code, gate.detail, "quality_gate"))
                continue
            good.append(enriched)

        try:
            inserted = self._sink.write(good)
        except Exception as exc:
            # Do not commit offsets: the whole batch is redelivered, and the idempotent sink absorbs the replay.
            result.committable = False
            result.dead_letters.append(DeadLetter("", "sink_failure", str(exc), "sink"))
            return result
        result.written = inserted
        result.duplicates = len(good) - inserted
        return result
