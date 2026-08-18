{{ config(materialized='table') }}

/*
  NexaCore ML Feature Mart: Inventory Stockout Risk Classification
  Grain: 1 row per inventory snapshot item (500 rows)
  Business Objective: Predict inventory stockout risk and classify items below reorder thresholds.
*/

SELECT
    i.inventory_id,
    i.product_id,
    p.product_name,
    p.category_name,
    i.warehouse_id,
    w.warehouse_name,
    w.region AS warehouse_location,
    i.snapshot_timestamp AS snapshot_date,
    i.quantity_on_hand,
    i.quantity_allocated,
    i.quantity_available,
    i.reorder_point,
    (i.reorder_point * 2) AS reorder_quantity,
    p.unit_cost,
    p.unit_price,
    ROUND((i.quantity_on_hand * p.unit_cost)::NUMERIC, 2) AS inventory_value_usd,
    ROUND((i.quantity_available / NULLIF(i.reorder_point, 0) * 30.0)::NUMERIC, 2) AS days_of_supply,
    -- Target Label: 1 if available inventory is strictly below reorder point (stockout risk), else 0
    CASE 
        WHEN i.quantity_available < i.reorder_point THEN 1 
        ELSE 0 
    END AS stockout_risk_flag_target
FROM {{ ref('fact_inventory_snapshot') }} i
JOIN {{ ref('dim_product') }} p ON i.product_id = p.product_id
JOIN {{ ref('dim_warehouse') }} w ON i.warehouse_id = w.warehouse_id
