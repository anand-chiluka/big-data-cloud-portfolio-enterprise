"""
STAR
Situation: A raw payment event says little about risk without the account's recent behavior.
Task: Add behavioral features in-stream, without a round trip to the warehouse per event.
Action: Keep a bounded per-account window keyed on event time and derive velocity, new-device, and country-hopping signals.
Result: Each event leaves the pipeline with explainable risk features and a rule-based score for analysts to query.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta

from src.validator import RiskEvent

VELOCITY_WINDOW = timedelta(minutes=5)
COUNTRY_WINDOW = timedelta(hours=1)
HIGH_AMOUNT = 1000.0


@dataclass(frozen=True)
class EnrichedEvent:
    event: RiskEvent
    tx_count_5m: int
    amount_sum_5m: float
    distinct_countries_1h: int
    is_new_device: bool
    risk_flags: tuple[str, ...]
    risk_score: int


class FeatureEnricher:
    """In-memory, per-account state. State is bounded by the window length, not by stream length."""

    def __init__(self) -> None:
        self._history: dict[str, deque[RiskEvent]] = defaultdict(deque)
        self._devices: dict[str, set[str]] = defaultdict(set)

    def enrich(self, event: RiskEvent) -> EnrichedEvent:
        history = self._history[event.account_id]
        # Evict by event time so late-arriving but in-window events still count.
        cutoff = event.event_time - COUNTRY_WINDOW
        while history and history[0].event_time < cutoff:
            history.popleft()

        recent = [e for e in history if e.event_time >= event.event_time - VELOCITY_WINDOW]
        countries = {e.country for e in history} | {event.country}
        is_new_device = bool(self._devices[event.account_id]) and event.device_id not in self._devices[event.account_id]

        tx_count = len(recent) + 1
        amount_sum = sum(e.amount for e in recent) + event.amount
        flags: list[str] = []
        score = 0
        if tx_count >= 5:
            flags.append("high_velocity")
            score += 40
        if len(countries) >= 3:
            flags.append("country_hopping")
            score += 30
        if is_new_device:
            flags.append("new_device")
            score += 15
        if event.amount >= HIGH_AMOUNT:
            flags.append("high_amount")
            score += 15

        history.append(event)
        self._devices[event.account_id].add(event.device_id)
        return EnrichedEvent(
            event=event,
            tx_count_5m=tx_count,
            amount_sum_5m=round(amount_sum, 2),
            distinct_countries_1h=len(countries),
            is_new_device=is_new_device,
            risk_flags=tuple(flags),
            risk_score=min(score, 100),
        )
