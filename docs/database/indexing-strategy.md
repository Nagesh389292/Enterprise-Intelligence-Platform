# Indexing Design & Access Pattern Strategy
### NexaCore Enterprise Intelligence Platform

---

## 1. Indexing Principles

1. **Foreign Key Coverage**: Every foreign key column in both 3NF source and Star Schema fact tables is explicitly indexed to prevent full-table scans during relational JOINs.
2. **Selective Filtering & Date Range Pruning**: High-cardinality timestamp fields (`order_timestamp`, `recorded_at`, `occurred_at`, `date_key`) are indexed to optimize time-windowed queries and partition pruning.
3. **No Unnecessary Indexes**: Low-cardinality boolean fields or small lookup tables without join conditions are excluded to minimize index maintenance write overhead.

---

## 2. Source Schema Target Access Patterns & Indexes

| Table Name | Index Name | Indexed Columns | Justification / Access Pattern |
| :--- | :--- | :--- | :--- |
| `source.customers` | `idx_source_customers_segment` | `(segment_id)` | Fast lookup by customer segment tier |
| `source.customers` | `idx_source_customers_status` | `(account_status)` | Active vs. Churned customer filtering |
| `source.customer_addresses` | `idx_source_cust_addr_customer` | `(customer_id, address_type)` | Primary billing/shipping address resolution |
| `source.orders` | `idx_source_orders_customer` | `(customer_id)` | Customer order history lookups |
| `source.orders` | `idx_source_orders_timestamp` | `(order_timestamp)` | Daily/Monthly incremental ETL extractions |
| `source.order_items` | `idx_source_order_items_composite`| `(order_id, product_id)` | Fast order line item retrieval |
| `source.inventory` | `idx_source_inventory_product_wh` | `(product_id, warehouse_id)` | Stock availability check by warehouse |
| `source.machine_telemetry` | `idx_source_telemetry_machine_time`| `(machine_id, recorded_at DESC)`| Time-series sensor extraction per machine |

---

## 3. Analytics Schema Target Access Patterns & Indexes

| Table Name | Index Name | Indexed Columns | Justification / Access Pattern |
| :--- | :--- | :--- | :--- |
| `analytics.dim_customer` | `idx_analytics_dim_cust_id` | `(customer_id, is_current)`| SCD Type 2 active record lookups |
| `analytics.fact_orders` | `idx_analytics_fact_orders_date` | `(order_date_key)` | BI sales reporting by calendar date |
| `analytics.fact_order_items` | `idx_analytics_fact_order_items_prod`| `(product_key)` | Product revenue and volume aggregations |
| `analytics.fact_inventory_daily`| `idx_analytics_fact_inv_daily_date_wh`| `(date_key, warehouse_key)`| Daily warehouse stock level snapshots |
| `analytics.fact_machine_telemetry`| `idx_analytics_fact_telem_machine_time`| `(machine_key, timestamp_minute DESC)`| ML feature extraction for anomaly detection |
