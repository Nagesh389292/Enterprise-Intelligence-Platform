{{ config(materialized='table') }}

/*
  NexaCore ML Feature Mart: Customer Churn Prediction
  Grain: 1 row per customer (1,000 customers)
  Temporal Anti-Leakage Constraint:
    Feature calculation is strictly bounded by feature_cutoff_date ('2026-05-01').
    Only orders, support tickets, and CSAT ratings on or before the cutoff date
    are included in feature engineering. Target is observed post-cutoff.
*/

WITH cutoff AS (
    SELECT '2026-05-01'::DATE AS feature_cutoff_date
),

customer_base AS (
    SELECT
        c.customer_id,
        c.segment_name,
        c.primary_state_province,
        c.valid_from::DATE AS customer_created_date,
        (k.feature_cutoff_date - c.valid_from::DATE) AS account_tenure_days
    FROM {{ ref('dim_customer') }} c
    CROSS JOIN cutoff k
),

historical_orders AS (
    SELECT
        o.customer_id,
        COUNT(o.order_id) AS total_orders_to_cutoff,
        COALESCE(SUM(o.total_amount), 0.00) AS total_spend_to_cutoff,
        COALESCE(AVG(o.total_amount), 0.00) AS avg_order_value_to_cutoff,
        MAX(o.order_timestamp::DATE) AS last_order_date_to_cutoff
    FROM {{ ref('fact_orders') }} o
    CROSS JOIN cutoff k
    WHERE o.order_timestamp::DATE <= k.feature_cutoff_date
    GROUP BY o.customer_id
),

post_cutoff_orders AS (
    SELECT
        o.customer_id,
        COUNT(o.order_id) AS post_cutoff_order_count
    FROM {{ ref('fact_orders') }} o
    CROSS JOIN cutoff k
    WHERE o.order_timestamp::DATE > k.feature_cutoff_date
      AND o.order_timestamp::DATE <= k.feature_cutoff_date + INTERVAL '60 days'
    GROUP BY o.customer_id
),

historical_support AS (
    SELECT
        t.customer_id,
        COUNT(t.ticket_id) AS total_support_tickets_to_cutoff,
        AVG(t.csat_score) AS avg_csat_score_to_cutoff
    FROM {{ ref('fact_support_tickets') }} t
    CROSS JOIN cutoff k
    WHERE t.created_at::DATE <= k.feature_cutoff_date
    GROUP BY t.customer_id
)

SELECT
    cb.customer_id,
    cb.segment_name,
    cb.primary_state_province,
    cb.account_tenure_days,
    COALESCE(ho.total_orders_to_cutoff, 0) AS total_orders_to_cutoff,
    COALESCE(ho.total_spend_to_cutoff, 0.00) AS total_spend_to_cutoff,
    ROUND(COALESCE(ho.avg_order_value_to_cutoff, 0.00), 2) AS avg_order_value_to_cutoff,
    CASE 
        WHEN ho.last_order_date_to_cutoff IS NULL THEN 999
        ELSE (k.feature_cutoff_date - ho.last_order_date_to_cutoff)
    END AS recency_days_at_cutoff,
    COALESCE(hs.total_support_tickets_to_cutoff, 0) AS total_support_tickets_to_cutoff,
    ROUND(COALESCE(hs.avg_csat_score_to_cutoff, 0.00), 2) AS avg_csat_score_to_cutoff,
    k.feature_cutoff_date,
    -- Target Label: 1 if customer placed 0 orders in 60 days post-cutoff, else 0
    CASE 
        WHEN COALESCE(po.post_cutoff_order_count, 0) = 0 THEN 1 
        ELSE 0 
    END AS is_churned_target
FROM customer_base cb
CROSS JOIN cutoff k
LEFT JOIN historical_orders ho ON cb.customer_id = ho.customer_id
LEFT JOIN post_cutoff_orders po ON cb.customer_id = po.customer_id
LEFT JOIN historical_support hs ON cb.customer_id = hs.customer_id
