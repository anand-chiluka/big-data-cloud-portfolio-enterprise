# Real-Time Risk Signal Pipeline (Kafka -> Snowflake)

## What this project is

A small streaming worker that reads `payment_attempt` events from Kafka,
validates them, adds behavioral risk features in-stream, gates the output,
and writes to Snowflake with an idempotent `MERGE`. Failures are routed to
a dead-letter topic with a reason code.

## Flow

```
Kafka payments.raw
   -> validator.py       envelope + payload contract, reason-coded errors
   -> enrichment.py      per-account velocity, country-hopping, new-device, high-amount flags + score
   -> quality_gate.py    checks on the enriched row (score range, aggregate sanity, flag/score consistency)
   -> sink.py            MERGE ... WHEN NOT MATCHED on event_id (idempotent)
Kafka payments.dlq  <-   anything rejected, with stage + reason_code
```

## Design decisions

- **Reason codes, not exceptions, at the edges.** Every rejection carries a stable
  `reason_code` and `stage`, so dead letters can be counted and triaged.
- **At-least-once delivery, idempotent writes.** Offsets are committed only after
  the sink write succeeds, so a failed write redelivers the batch. The sink keys
  on `event_id`, so a replay changes nothing.
- **Event-time windows.** Enrichment evicts by event time, not arrival time, and
  state is bounded by the window length.
- **Pure core, thin Kafka shell.** `RiskPipeline.process_batch` has no Kafka
  dependency, so the logic is unit-tested without a broker.

## What has been validated, and what has not

- **Run:** 19 unit tests (`pytest`) covering validation reason codes, windowed
  enrichment, dead-letter routing, replay idempotency, and sink-failure behavior.
  The sink in these tests is an in-memory double with the same first-write-wins
  rule as the MERGE.
- **Not run:** a live Kafka broker, a live Snowflake account, and the `MERGE`
  SQL against real Snowflake. `SnowflakeMergeSink` and `consumer.py` are written
  but not exercised end to end. The Docker build is also untested.

## Run the tests

```bash
cd projects/shared_event_streaming/kafka_snowflake_risk_pipeline
pip install pytest
pytest -q
```

## Known limitations / what I'd add next

- Enrichment state is in process memory, so it is lost on restart and not shared
  across consumers. Production would use a keyed state store (for example Kafka
  Streams or Flink) with partitioning by account.
- The risk score is rule-based and illustrative, not a trained model.
- The MERGE runs row by row. At volume it should be a staged batch MERGE.
- The Snowflake `PRIMARY KEY` is informational only. Uniqueness comes from the MERGE.
