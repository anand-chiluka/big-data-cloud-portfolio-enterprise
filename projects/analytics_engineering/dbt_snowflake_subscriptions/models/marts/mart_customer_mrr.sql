-- Mart: governed, business-facing MRR (Monthly Recurring Revenue) by customer.
-- This is the table BI tools and analysts query directly. The definition
-- of "MRR" lives here exactly once: active subscriptions' current_mrr_usd,
-- summed per customer. No dashboard should ever recompute this logic
-- independently -- that's exactly the class of bug this model prevents.

with subscription_state as (

    select * from {{ ref('int_subscription_current_state') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

customer_mrr as (

    select
        c.customer_id,
        c.country_code,
        c.acquisition_channel,
        c.signup_date,
        count(distinct case when s.is_active then s.subscription_id end)      as active_subscription_count,
        coalesce(sum(case when s.is_active then s.current_mrr_usd end), 0)    as total_mrr_usd

    from customers c
    left join subscription_state s
        on c.customer_id = s.customer_id

    group by 1, 2, 3, 4

)

select * from customer_mrr
