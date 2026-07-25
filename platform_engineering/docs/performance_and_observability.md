# Performance and Observability Standards

## Metric naming convention

Every metric across every project in this repo follows one pattern:

```
{namespace}.{connector_or_sink_name}.{measurement}_{unit}
```

Examples: `data_platform.sql_connector.extract_duration_seconds`,
`data_platform.risk_pipeline.records_rejected_total`,
`data_platform.snowflake_sink.write_latency_seconds`.

Why this matters more than it sounds like it should: without a
convention, every engineer invents their own naming, and six months
later nobody can build a dashboard that spans two pipelines without a
translation layer. A convention costs nothing to follow and saves real
time the first time someone needs a cross-pipeline view.

## The four golden signals, applied to this platform

Borrowed from Google's SRE book, since they generalize cleanly to data
pipelines, not just web services:

| Signal | What it means here | Example metric |
|---|---|---|
| **Latency** | Time from record landing in a source to being queryable in a sink | `extract_duration_seconds`, `end_to_end_latency_seconds` |
| **Traffic** | Volume flowing through the system | `records_extracted_total`, `bytes_processed_total` |
| **Errors** | Rate of failed/rejected records or failed pipeline runs | `records_rejected_total`, `pipeline_run_failures_total` |
| **Saturation** | How close a resource is to its limit | `consumer_lag`, `queue_depth`, `warehouse_credit_utilization_pct` |

## SLIs and SLOs (see `observability/src/slo.py` for the executable version)

| SLO | Target | Why this number |
|---|---|---|
| Extraction latency (p95) | ≤ 30 seconds | Fast enough that a human debugging a live incident isn't waiting on the pipeline itself |
| Data freshness | ≤ 15 minutes | Matches the batch connector's 15-minute CronJob schedule; freshness SLOs should always trace back to an actual scheduling decision, not be picked arbitrarily |
| Extraction error rate | ≤ 5% | High enough to tolerate normal upstream data quality noise, low enough that a real regression (e.g. 20% reject rate) triggers immediately |
| Pipeline availability | ≥ 99.9% | ~43 minutes of allowed downtime per month; realistic for a team without 24/7 dedicated on-call, appropriately strict for anything feeding Risk or Compliance |

**Important honesty note on these numbers:** these are reasonable
starting points for a portfolio project demonstrating the practice, not
numbers derived from a real production system's historical p50/p95/p99.
In an actual production environment, SLOs get set from real historical
baselines and revisited quarterly with the teams who consume the data,
not picked once by the platform team in isolation.

## Performance patterns actually used in this codebase

**Incremental extraction over full re-scans.** `SQLConnector` and
`APIConnector` both track a cursor and only pull what changed, rather
than re-extracting everything on every run. At any real data volume,
full re-scans are the single most common self-inflicted performance
problem in a data platform.

**Batch writes over row-by-row.** Every sink in this repo batches
records before writing (Snowflake's staged `PUT` + `COPY INTO`, S3's
partitioned file writes) rather than issuing one `INSERT` per record,
which is 10-100x slower at any meaningful volume and is one of the most
common reasons a "working" pipeline falls over the first time real
traffic hits it.

**In-stream computation over batch recomputation for time-sensitive
signals.** The risk pipeline computes velocity and amount-anomaly
features as events arrive, not in a nightly batch job, since a risk
signal that's 12 hours stale is a much weaker signal.

## What I would add for true production-scale performance work

- **Load testing** before every major release: replay a realistic
  multiple of production traffic against a staging environment and
  confirm p95/p99 latency holds, not just that the pipeline doesn't
  crash.
- **Distributed tracing** (OpenTelemetry) across connector -> sink
  boundaries, so a slow end-to-end run can be attributed to a specific
  stage instead of guessed at from logs.
- **Cost-per-record tracking** alongside latency: a pipeline that's fast
  but burns 10x the Snowflake credits it needs to isn't actually a
  performance win, it's a cost problem wearing a performance costume.
- **Backpressure handling** for the streaming path: when a downstream
  sink slows down, the consumer should apply backpressure (pause
  consumption) rather than buffer unboundedly in memory until the pod
  OOMs.
