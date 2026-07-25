-- Singular test: MRR should never be negative. A negative value here
-- would indicate a bug in the current-state or aggregation logic, not
-- a valid business state. dbt test fails (returns rows) if this
-- condition is ever violated.

select
    customer_id,
    total_mrr_usd
from {{ ref('mart_customer_mrr') }}
where total_mrr_usd < 0
