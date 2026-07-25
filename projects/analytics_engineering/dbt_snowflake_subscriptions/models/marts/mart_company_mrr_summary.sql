-- Mart: single-row company-wide MRR summary. This is the exact kind of
-- "one governed number" table that prevents the classic problem of Finance,
-- Sales, and a self-serve BI tool each calculating total MRR slightly
-- differently and arriving at three different numbers for the same month.

with customer_mrr as (

    select * from {{ ref('mart_customer_mrr') }}

),

summary as (

    select
        sum(total_mrr_usd)              as company_mrr_usd,
        sum(active_subscription_count)  as company_active_subscriptions,
        count(distinct customer_id)     as total_customers,
        count(distinct case when active_subscription_count > 0 then customer_id end) as paying_customers

    from customer_mrr

)

select * from summary
