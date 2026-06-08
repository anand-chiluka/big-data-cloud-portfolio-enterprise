"""
STAR
Situation: A strong portfolio needs sample data that exercises structured, semi structured, and unstructured ingestion.
Task: Generate deterministic local datasets in multiple compression formats.
Action: Write orders as CSV gzip, clickstream as JSON Lines bz2 and gzip, and support notes as zipped text.
Result: Every project can be tested locally without relying on proprietary data.
"""

from __future__ import annotations

import bz2
import csv
import gzip
import json
import random
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample"


def generate_orders() -> list[dict[str, object]]:
    random.seed(7)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(1, 101):
        rows.append(
            {
                "order_id": f"ord_{index:05d}",
                "customer_id": f"cust_{random.randint(1, 25):04d}",
                "order_ts": (start + timedelta(minutes=index * 13)).isoformat(),
                "amount": round(random.uniform(5, 900), 2),
                "currency": "USD",
                "channel": random.choice(["web", "mobile", "partner"]),
            }
        )
    return rows


def write_orders(rows: list[dict[str, object]]) -> None:
    path = SAMPLE / "structured" / "orders.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_clickstream() -> None:
    path_bz2 = SAMPLE / "semi_structured" / "clickstream.jsonl.bz2"
    path_gz = SAMPLE / "semi_structured" / "clickstream.jsonl.gz"
    path_bz2.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for index in range(1, 151):
        events.append(
            {
                "event_id": f"evt_{index:05d}",
                "user_id": f"user_{random.randint(1, 40):04d}",
                "event_ts": (start + timedelta(seconds=index * 17)).isoformat(),
                "page": random.choice(["home", "search", "checkout", "pricing", "docs"]),
                "device": random.choice(["ios", "android", "web"]),
                "campaign": random.choice([None, "organic", "spring_launch", "retargeting"]),
            }
        )
    for path, opener in [(path_bz2, bz2.open), (path_gz, gzip.open)]:
        with opener(path, "wt", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")


def write_support_notes() -> None:
    path = SAMPLE / "unstructured" / "support_notes.txt.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    notes = """ticket_id=1001 priority=high customer reports delayed order confirmation\n
    ticket_id=1002 priority=medium user cannot locate invoice after checkout\n
    ticket_id=1003 priority=low feature request for bulk export\n"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("support_notes.txt", notes)


def main() -> None:
    rows = generate_orders()
    write_orders(rows)
    write_clickstream()
    write_support_notes()
    print(f"Generated sample files under {SAMPLE}")


if __name__ == "__main__":
    main()
