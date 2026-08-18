# Fact Table Grains, Lineage & Temporal Leakage Documentation

## Architectural Overview

This document specifies the official Gold layer fact grains, business keys, measures, temporal leakage prevention rules, and reconciliation control totals for the NexaCore Enterprise Data Warehouse (`analytics.*` schema).

---

## 1. Fact Table Definitions & Grains

### 1. `fact_orders`
* **Grain**: 1 row per purchase order.
* **Natural / Business Key**: `order_id` (UUID).
* **Dimension Keys**: `customer_id` (`dim_customer`), `shipping_address_id` (`dim_customer`), `channel_id`, `date_key` (`dim_date`).
* **Measures**: `total_amount` (NUMERIC).
* **Derived Measures**: `derived_actual_delivery_date` (explicitly labeled synthetic timestamp), `derived_delivery_delay_days` (INTEGER).
* **Timestamp**: `order_timestamp` (TIMESTAMPTZ).
* **Source Tables**: `source.orders` via `stg_orders`.
* **Reconciliation Rule**: Row count must match `source.orders` exactly (10,000 rows). Sum of `total_amount` must equal `$18,274,577.78`.

### 2. `fact_order_items`
* **Grain**: 1 row per purchase order line item.
* **Natural / Business Key**: `order_item_id` (BIGINT).
* **Dimension Keys**: `order_id` (`fact_orders`), `product_id` (`dim_product`), `date_key` (`dim_date`).
* **Measures**: `quantity` (INT), `unit_price` (NUMERIC), `discount_amount` (NUMERIC), `unit_cost` (NUMERIC).
* **Derived Measures**: `gross_revenue` (`quantity * unit_price`), `net_revenue` (`(quantity * unit_price) - discount_amount`), `gross_profit_margin` (`net_revenue - (quantity * unit_cost)`).
* **Timestamp**: `o.order_timestamp` (TIMESTAMPTZ).
* **Source Tables**: `source.order_items` joined with `source.orders` and `source.products`.
* **Reconciliation Rule**: Row count must match `source.order_items` exactly (35,193 rows). Sum of `quantity` must equal `193,309` units. Sum of `net_revenue` must equal `$18,274,577.78`.

### 3. `fact_inventory_snapshot`
* **Grain**: 1 row per product × warehouse inventory count snapshot.
* **Natural / Business Key**: `inventory_id` (BIGINT).
* **Dimension Keys**: `warehouse_id` (`dim_warehouse`), `product_id` (`dim_product`), `date_key` (`dim_date`).
* **Measures**: `quantity_on_hand` (INT), `quantity_allocated` (INT), `quantity_available` (`quantity_on_hand - quantity_allocated`).
* **Derived Measures**: `reorder_point` (INT), `is_below_reorder_point` (BOOLEAN).
* **Timestamp**: `snapshot_timestamp` (`last_count_date` TIMESTAMPTZ).
* **Source Tables**: `source.inventory` joined with `source.products`.
* **Reconciliation Rule**: Truthful grain preserves source snapshot size (500 rows). Sum of `quantity_on_hand` must equal `184,520` units. Sum of `quantity_allocated` must equal `28,431` units.

### 4. `fact_machine_telemetry`
* **Grain**: 1 row per machine × 1-minute aggregation interval.
* **Natural / Business Key**: `telemetry_minute_key` (`MD5(machine_id + minute_timestamp)`).
* **Dimension Keys**: `machine_id` (`dim_machine`), `date_key` (`dim_date`).
* **Measures**: `event_count` (INT), `avg_temperature_c` (FLOAT), `max_temperature_c` (FLOAT), `min_temperature_c` (FLOAT), `avg_vibration_rms` (FLOAT), `max_vibration_rms` (FLOAT), `avg_pressure_psi` (FLOAT), `avg_power_kw` (FLOAT).
* **Derived Measures**: `type_max_temperature_c`, `type_max_vibration_rms`, `temperature_anomaly_flag` (BOOLEAN), `vibration_anomaly_flag` (BOOLEAN).
* **Timestamp**: `minute_timestamp` (TIMESTAMPTZ).
* **Source Tables**: `source.machine_telemetry` aggregated by minute and joined with `source.machines` & `source.machine_types`.
* **Raw Preservation Note**: Raw IoT sensor telemetry remains untouched in `source.machine_telemetry` (100,000 rows).
* **Reconciliation Rule**: 100,000 raw sensor events aggregate to 29,800 1-minute records across 50 machines over 7 full days (aggregation ratio 3.36:1).

### 5. `fact_maintenance_events`
* **Grain**: 1 row per machine maintenance event.
* **Natural / Business Key**: `maintenance_id` (UUID).
* **Dimension Keys**: `machine_id` (`dim_machine`), `date_key` (`dim_date`).
* **Measures**: `cost_usd` (NUMERIC).
* **Derived Measures**: `derived_downtime_hours` (FLOAT).
* **Timestamp**: `performed_at` (TIMESTAMPTZ).
* **Source Tables**: `source.maintenance_events`.
* **Reconciliation Rule**: Row count must match `source.maintenance_events` exactly (10 rows).

### 6. `fact_support_tickets`
* **Grain**: 1 row per customer service support ticket.
* **Natural / Business Key**: `ticket_id` (UUID).
* **Dimension Keys**: `customer_id` (`dim_customer`), `order_id` (`fact_orders`), `date_key` (`dim_date`).
* **Measures**: `resolution_time_hours` (FLOAT), `csat_score` (INT).
* **Derived Measures**: `csat_survey_id`, `csat_feedback_text`, `csat_submitted_at`.
* **Timestamp**: `created_at` (TIMESTAMPTZ).
* **Source Tables**: `source.support_tickets` left joined with `source.customer_satisfaction`.
* **Reconciliation Rule**: Row count must match `source.support_tickets` exactly (2,500 rows). Linked CSAT count must equal `1,748` surveys with average score `4.15 / 5.0`.

---

## 2. Temporal Leakage Prevention Rules for ML

To ensure downstream ML models train on true historical signals without seeing future outcomes:

1. **Customer Churn**:
   - **Feature Horizon**: All customer order counts, ticket counts, and total spend features must be computed strictly prior to observation cutoff date $T_{cutoff}$.
   - **Target Window**: Churn target flag evaluates customer activity in interval $[T_{cutoff}, T_{cutoff} + 90\text{ days}]$.

2. **Demand Forecasting**:
   - **Feature Horizon**: Historical order item quantities aggregated up to observation day $D$.
   - **Target Horizon**: Product demand forecasted for days $D+1$ through $D+7$.

3. **Inventory Stockout Risk**:
   - **Feature Horizon**: `quantity_available` and `reorder_point` captured on snapshot date `2026-06-30`.
   - **Target Horizon**: Stockout events evaluated in subsequent 30-day window.

4. **Predictive Equipment Failure**:
   - **Feature Horizon**: Rolling 1-minute telemetry metrics (`avg_temperature_c`, `max_vibration_rms`, anomaly flags) computed in rolling window $[T - 24\text{ hours}, T]$.
   - **Target Horizon**: Machine failure event occurring within window $[T, T + 72\text{ hours}]$.

---

## 3. Empirical Control Totals Reconciliation

| Fact Table | Metric | Silver Source Value | Gold Mart Value | Variance | Reconciliation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`fact_orders`** | Row Count | 10,000 | 10,000 | 0 | **RECONCILED** |
| **`fact_orders`** | Total Revenue | $18,274,577.78 | $18,274,577.78 | $0.00 | **RECONCILED** |
| **`fact_order_items`** | Row Count | 35,193 | 35,193 | 0 | **RECONCILED** |
| **`fact_order_items`** | Net Revenue | $18,274,577.78 | $18,274,577.78 | $0.00 | **RECONCILED** |
| **`fact_order_items`** | Quantity Sold | 193,309 units | 193,309 units | 0 | **RECONCILED** |
| **`fact_order_items`** | Discount Total | $1,056,586.32 | $1,056,586.32 | $0.00 | **RECONCILED** |
| **`fact_inventory_snapshot`** | Snapshot Rows | 500 | 500 | 0 | **RECONCILED** |
| **`fact_inventory_snapshot`** | On-Hand Quantity | 184,520 units | 184,520 units | 0 | **RECONCILED** |
| **`fact_inventory_snapshot`** | Allocated Quantity | 28,431 units | 28,431 units | 0 | **RECONCILED** |
| **`fact_machine_telemetry`** | Raw Event Count | 100,000 | 100,000 (Silver) | 0 | **PRESERVED** |
| **`fact_machine_telemetry`** | 1-min Aggregate Rows | N/A | 29,800 | N/A (3.36:1 Ratio) | **RECONCILED** |
| **`fact_maintenance_events`** | Row Count | 10 | 10 | 0 | **RECONCILED** |
| **`fact_support_tickets`** | Row Count | 2,500 | 2,500 | 0 | **RECONCILED** |
| **`fact_support_tickets`** | Linked CSAT Surveys | 1,748 | 1,748 | 0 | **RECONCILED** |
| **`fact_support_tickets`** | Avg CSAT Score | 4.15 / 5.0 | 4.15 / 5.0 | 0.00 | **RECONCILED** |

---

## 4. Relationship & Orphan Key Audit

| Fact Table | Foreign Key Column | Dimension Target | Orphan Count | FK Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| `fact_orders` | `customer_id` | `dim_customer` | **0** | **PASSED** |
| `fact_order_items` | `product_id` | `dim_product` | **0** | **PASSED** |
| `fact_order_items` | `order_id` | `fact_orders` | **0** | **PASSED** |
| `fact_inventory_snapshot` | `warehouse_id` | `dim_warehouse` | **0** | **PASSED** |
| `fact_inventory_snapshot` | `product_id` | `dim_product` | **0** | **PASSED** |
| `fact_machine_telemetry` | `machine_id` | `dim_machine` | **0** | **PASSED** |
| `fact_maintenance_events` | `machine_id` | `dim_machine` | **0** | **PASSED** |
| `fact_support_tickets` | `customer_id` | `dim_customer` | **0** | **PASSED** |

**Orphan Status**: **0 orphan dimension keys across all Gold fact relationships**.
