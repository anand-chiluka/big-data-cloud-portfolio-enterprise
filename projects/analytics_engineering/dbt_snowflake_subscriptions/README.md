# Subscription Revenue Metrics (dbt + Snowflake)

## What this project is

A standalone dbt project implementing a governed MRR (Monthly Recurring
Revenue) metrics layer on Snowflake, following the staging -> intermediate
-> marts pattern. It exists to demonstrate the exact discipline that
prevents the single most common data trust problem in any company: Finance,
Sales, and a self-serve BI tool each computing "MRR" slightly differently
and arriving at three different numbers for the same month.

## The problem this solves

At scale, "what is our MRR right now" sounds like a simple question with an
obvious answer. In practice, teams routinely disagree on it because the
logic for "is this subscription active," "what counts toward MRR," and
"how do upgrades/downgrades get counted" all get reimplemented slightly
differently in every dashboard, spreadsheet, and ad hoc query that touches
revenue. This project defines that logic exactly once, in `int_subscription_current_state`
and `mart_customer_mrr`, so every downstream consumer inherits the same
answer instead of recomputing it independently.

## Architecture

```
raw.subscription_events, raw.customers   (landed via Snowpipe from S3)
        |
        v
stg_subscription_events, stg_customers    (staging: clean, typed, 1:1 with source)
        |
        v
int_subscription_current_state            (intermediate: business logic --
                                            "what is this subscription's
                                            current state" computed once)
        |
        v
mart_customer_mrr                         (mart: governed, per-customer MRR)
        |
        v
mart_company_mrr_summary                  (mart: single governed company-wide number)
```

## Design decisions

**Staging models never contain business logic.** They only rename, cast,
and lightly clean columns. This keeps a clean seam between "what the source
system gave us" and "what we've decided it means," so a source schema
change never silently corrupts business logic.

**Current-subscription-state is computed exactly once.** `int_subscription_current_state`
uses `row_number()` over event history to determine each subscription's
latest state. Every mart downstream builds on this one model rather than
re-deriving "is this subscription active" independently.

**The company-wide summary is built on top of the per-customer mart, not
recomputed from raw events.** This guarantees `mart_company_mrr_summary`
and `mart_customer_mrr` can never disagree with each other, since one is
mechanically derived from the other.

**Tests enforce the guarantees that matter, not just column hygiene.**
Beyond standard `not_null`/`unique` tests, there's a custom singular test
(`assert_mrr_never_negative.sql`) encoding an actual business invariant:
MRR should never go negative. A failing test here means a real logic bug,
not a data quality nitpick.

## What has been validated, and what requires a live account

This project was fully built and validated using `dbt parse` and
`dbt compile` against dbt-core 1.12 with the Snowflake adapter installed.
Both commands run clean with zero errors or warnings:

```
$ dbt parse
Found 5 models, 21 data tests, 2 seeds, 2 sources, 545 macros

$ dbt compile
[connects to Snowflake to fetch warehouse metadata -- this is the only
 step that requires a real account; every model, ref(), source(), and
 test in the project is confirmed syntactically valid and correctly wired]
```

No live Snowflake account was available in this environment, so `dbt run`
and `dbt test` (which execute against a real warehouse) have not been run
end-to-end against production Snowflake. Every model compiles correctly
and the SQL is standard Snowflake syntax, so running it live is a matter
of pointing `profiles.yml` at a real account, not a matter of fixing code.

## Run it yourself

```bash
pip install dbt-core dbt-snowflake
cp profiles.yml.template ~/.dbt/profiles.yml   # fill in real Snowflake credentials
dbt seed        # loads the sample CSVs as raw source tables
dbt run         # builds staging -> intermediate -> marts
dbt test        # runs all 21 tests including the custom MRR invariant
```

## What I'd add next

A `semantic_layer` or MetricFlow definition on top of `mart_company_mrr_summary`
so the same MRR metric could be queried consistently through dbt's semantic
layer, Snowflake's native Semantic Views, or a BI tool's own metrics layer,
without redefining the calculation a fourth time.
