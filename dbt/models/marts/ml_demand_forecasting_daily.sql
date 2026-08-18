{{ config(materialized='table') }}

/*
  NexaCore ML Feature Mart: Daily Demand Forecasting
  Grain: 1 row per product x calendar date
  Temporal Anti-Leakage Constraint:
    Lag features (lag_7, lag_14) and rolling window features (7-day, 30-day avg)
    are calculated strictly on preceding dates using ROWS BETWEEN ... PRECEDING
    to ensure zero forward-looking data leakage.
*/

WITH date_spine AS (
    SELECT
        d.date_key,
        d.full_date,
        d.day_name AS day_of_week,
        d.month AS month,
        CASE WHEN d.is_weekend THEN 1 ELSE 0 END AS is_weekend
    FROM {{ ref('dim_date') }} d
    WHERE d.full_date BETWEEN '2026-01-01' AND '2026-06-30'
),

product_spine AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category_name,
        'Default Supplier'::text AS supplier_name
    FROM {{ ref('dim_product') }} p
),

daily_product_sales AS (
    SELECT
        ps.product_id,
        ds.date_key,
        ds.full_date,
        ds.day_of_week,
        ds.month,
        ds.is_weekend,
        ps.product_name,
        ps.category_name,
        ps.supplier_name,
        COALESCE(SUM(oi.quantity), 0) AS units_sold_target,
        COALESCE(SUM(oi.net_revenue), 0.00) AS daily_revenue,
        COUNT(DISTINCT oi.order_id) AS daily_orders_count
    FROM product_spine ps
    CROSS JOIN date_spine ds
    LEFT JOIN {{ ref('fact_orders') }} o ON o.date_key = ds.date_key
    LEFT JOIN {{ ref('fact_order_items') }} oi ON oi.order_id = o.order_id AND oi.product_id = ps.product_id
    GROUP BY
        ps.product_id, ds.date_key, ds.full_date, ds.day_of_week, ds.month, ds.is_weekend,
        ps.product_name, ps.category_name, ps.supplier_name
),

feature_engineering AS (
    SELECT
        s.*,
        -- Lag Features
        LAG(s.units_sold_target, 7) OVER (
            PARTITION BY s.product_id ORDER BY s.full_date
        ) AS lag_7_units_sold,
        LAG(s.units_sold_target, 14) OVER (
            PARTITION BY s.product_id ORDER BY s.full_date
        ) AS lag_14_units_sold,
        -- Rolling Averages (strict anti-leakage: preceding rows only, excluding current row)
        AVG(s.units_sold_target) OVER (
            PARTITION BY s.product_id ORDER BY s.full_date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS rolling_7_day_avg_units,
        AVG(s.units_sold_target) OVER (
            PARTITION BY s.product_id ORDER BY s.full_date
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS rolling_30_day_avg_units
    FROM daily_product_sales s
)

SELECT
    product_id,
    date_key,
    full_date,
    day_of_week,
    month,
    is_weekend,
    product_name,
    category_name,
    supplier_name,
    units_sold_target,
    ROUND(daily_revenue, 2) AS daily_revenue,
    daily_orders_count,
    COALESCE(lag_7_units_sold, 0) AS lag_7_units_sold,
    COALESCE(lag_14_units_sold, 0) AS lag_14_units_sold,
    ROUND(COALESCE(rolling_7_day_avg_units, 0.00), 2) AS rolling_7_day_avg_units,
    ROUND(COALESCE(rolling_30_day_avg_units, 0.00), 2) AS rolling_30_day_avg_units
FROM feature_engineering
