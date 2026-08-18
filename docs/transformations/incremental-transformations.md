# Incremental Transformation & Refresh Mechanics
### NexaCore Enterprise Intelligence Platform

---

## 📌 Incremental Modeling Overview

To maintain low latency and high query performance as Gold data grows, fact tables (`fact_orders`, `fact_order_items`, `fact_inventory_daily`, `fact_machine_telemetry`) use **Incremental Refreshes**.

Rather than dropping and rebuilding entire multi-gigabyte tables, incremental models evaluate newly ingested Silver records since the last successful run watermark.

---

## 1. dbt Incremental Pattern (`is_incremental()`)

```sql
-- dbt Incremental Fact Model Template: fact_orders.sql
{{ config(
    materialized='incremental',
    unique_key='order_number',
    on_schema_change='append_new_columns'
) }}

SELECT 
    MD5(o.order_number) AS order_key,
    o.order_number,
    d.date_key,
    c.customer_key,
    o.channel_id,
    o.shipping_address_id,
    o.order_status,
    o.total_amount,
    o._ingestion_batch_id,
    o._ingested_at
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('dim_customer') }} c ON o.customer_id = c.customer_id AND c.is_current = TRUE
JOIN {{ ref('dim_date') }} d ON o.order_timestamp::DATE = d.full_date

{% if is_incremental() %}
    -- High Watermark Filter: Process only records ingested after max _ingested_at in target
    WHERE o._ingested_at > (SELECT MAX(_ingested_at) FROM {{ this }})
{% endif %}
```

---

## 2. Watermark State & Late-Arriving Data Strategy

### 2.1 Watermark Buffer Window
To accommodate late-arriving source records, incremental filters incorporate a **Lookback Buffer Window**:

$$\text{Watermark\_Cutoff} = \max(\text{\_ingested\_at}) - \text{INTERVAL } '3 \text{ DAYS'}$$

```sql
{% if is_incremental() %}
    WHERE o._ingested_at > (SELECT COALESCE(MAX(_ingested_at) - INTERVAL '3 DAYS', '1970-01-01') FROM {{ this }})
{% endif %}
```

### 2.2 Late-Arriving Foreign Keys (Orphan Dimensions)
If an order references a `customer_id` not yet present in `dim_customer`:
* The dbt model joins using `LEFT JOIN`.
* Missing dimension surrogate keys default to `-1` (`Unknown Customer`).
* An orphan dimension audit query alerts operators in `audit.data_quality_audit_logs`.
