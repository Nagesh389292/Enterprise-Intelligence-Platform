# Analytical Data Mart Dictionary (Dimensional Star Schema)
### NexaCore Enterprise Data Warehouse (Gold Layer)

This document defines the **Dimensional Star Schema Model** implemented in the **Gold Layer** (PostgreSQL / dbt). The analytical layer transforms normalized 3NF source data into optimized dimension tables (`dim_*`) and fact tables (`fact_*`) for BI reporting and Machine Learning pipelines.

---

## 1. Dimension Tables Summary

| Dimension Name | Source Tables | Primary / Surrogate Key | SCD Strategy | Business Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `dim_customers` | `customers`, `customer_segments` | `customer_key` (INT) | **SCD Type 2** | Historical customer attributes, segment history, credit tiers |
| `dim_products` | `products`, `product_categories` | `product_key` (INT) | **SCD Type 1** | Current product catalog, pricing, SKU mappings |
| `dim_suppliers` | `suppliers` | `supplier_key` (INT) | **SCD Type 1** | Vendor lead times, quality ratings, country |
| `dim_warehouses` | `warehouses` | `warehouse_key` (INT) | **SCD Type 1** | Storage locations, geographic regions, capacities |
| `dim_machines` | `machines`, `machine_types` | `machine_key` (INT) | **SCD Type 2** | Equipment specs, status changes, factory locations |
| `dim_date` | Date Generator | `date_key` (INT: YYYYMMDD) | **Static** | Standard calendar dimension (day, week, month, quarter, holiday flags) |

---

## 2. Fact Tables & Explicit Grains

### 2.1 `fact_orders`
* **Business Purpose**: Tracks header-level sales orders, revenue totals, fulfillment performance, and customer purchasing activity.
* **EXPLICIT GRAIN**: **One record per individual purchase order header (`order_id`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `order_key` | BIGINT | NOT NULL | PK | Unique surrogate key for fact order |
| `order_id` | UUID | NOT NULL | - | Degenerate dimension (source order ID) |
| `order_number` | VARCHAR(50) | NOT NULL | - | Degenerate dimension (order reference) |
| `customer_key` | INT | NOT NULL | FK -> dim_customers | Customer associated at order time (SCD Type 2 match) |
| `channel_key` | INT | NOT NULL | FK | Sales channel surrogate key |
| `shipping_address_id`| UUID | NOT NULL | - | Degenerate shipping location ID |
| `order_date_key` | INT | NOT NULL | FK -> dim_date | Date key of order placement (`YYYYMMDD`) |
| `promised_date_key` | INT | NULL | FK -> dim_date | Date key of expected delivery |
| `order_status` | VARCHAR(20) | NOT NULL | - | Status (DELIVERED, SHIPPED, CANCELLED) |
| `total_order_amount`| NUMERIC(14,2) | NOT NULL | - | Gross total order value ($) |
| `order_item_count` | INT | NOT NULL | - | Total number of line item SKUs |
| `is_delayed` | INT | NOT NULL | - | Binary indicator (1 if delivered after promised date, else 0) |
| `created_at` | TIMESTAMPTZ | NOT NULL | - | Ingestion audit timestamp |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Lineage tracking pipeline batch identifier |

---

### 2.2 `fact_order_items`
* **Business Purpose**: Deep line-item sales analysis, SKU popularity, profit margin calculation, and product basket association.
* **EXPLICIT GRAIN**: **One record per individual line item on a purchase order (`order_id` + `product_id`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `order_item_key` | BIGINT | NOT NULL | PK | Unique surrogate key for line item |
| `order_id` | UUID | NOT NULL | FK -> fact_orders | Foreign key referencing parent order |
| `product_key` | INT | NOT NULL | FK -> dim_products | Product SKU surrogate key |
| `customer_key` | INT | NOT NULL | FK -> dim_customers | Denormalized customer reference for line item queries |
| `order_date_key` | INT | NOT NULL | FK -> dim_date | Order transaction date key (`YYYYMMDD`) |
| `quantity` | INT | NOT NULL | - | Units purchased |
| `unit_price` | NUMERIC(10,2) | NOT NULL | - | Actual selling price per unit ($) |
| `unit_cost` | NUMERIC(10,2) | NOT NULL | - | Product cost at time of order ($) |
| `gross_revenue` | NUMERIC(12,2) | NOT NULL | - | `quantity * unit_price` |
| `discount_amount` | NUMERIC(10,2) | NOT NULL | - | Discount subtracted ($) |
| `net_revenue` | NUMERIC(12,2) | NOT NULL | - | `gross_revenue - discount_amount` |
| `gross_profit` | NUMERIC(12,2) | NOT NULL | - | `net_revenue - (quantity * unit_cost)` |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Lineage tracking pipeline batch ID |

---

### 2.3 `fact_inventory_daily`
* **Business Purpose**: Periodic snapshot of warehouse inventory levels, stockout risk tracking, and safety stock monitoring.
* **EXPLICIT GRAIN**: **One record per product SKU per warehouse location per calendar day (`date_key` + `warehouse_key` + `product_key`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `inventory_snapshot_key` | BIGINT | NOT NULL | PK | Unique surrogate key for snapshot record |
| `date_key` | INT | NOT NULL | FK -> dim_date | Snapshot calendar date (`YYYYMMDD`) |
| `warehouse_key` | INT | NOT NULL | FK -> dim_warehouses | Warehouse location surrogate key |
| `product_key` | INT | NOT NULL | FK -> dim_products | Product SKU surrogate key |
| `quantity_on_hand` | INT | NOT NULL | - | Physical stock on hand |
| `quantity_allocated`| INT | NOT NULL | - | Reserved stock for open orders |
| `quantity_available`| INT | NOT NULL | - | Net salable stock (`on_hand - allocated`) |
| `reorder_point` | INT | NOT NULL | - | Reorder threshold reference |
| `is_out_of_stock` | INT | NOT NULL | - | Binary indicator (1 if `quantity_available == 0`) |
| `is_low_stock` | INT | NOT NULL | - | Binary indicator (1 if `quantity_available <= reorder_point`) |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Lineage tracking pipeline batch ID |

---

### 2.4 `fact_machine_telemetry`
* **Business Purpose**: Time-series aggregation of high-frequency IoT sensor streams for industrial anomaly detection.
* **EXPLICIT GRAIN**: **One record per machine per 1-minute aggregation interval (`machine_key` + `timestamp_minute`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `telemetry_fact_key` | BIGINT | NOT NULL | PK | Unique telemetry fact key |
| `machine_key` | INT | NOT NULL | FK -> dim_machines | Machine surrogate key |
| `timestamp_minute` | TIMESTAMPTZ | NOT NULL | - | Start of 1-minute aggregation interval |
| `date_key` | INT | NOT NULL | FK -> dim_date | Date key (`YYYYMMDD`) |
| `avg_temperature_c` | NUMERIC(5,2) | NOT NULL | - | Mean temperature over 1-min interval |
| `max_temperature_c` | NUMERIC(5,2) | NOT NULL | - | Peak temperature over 1-min interval |
| `avg_vibration_rms` | NUMERIC(5,2) | NOT NULL | - | Mean vibration RMS |
| `max_vibration_rms` | NUMERIC(5,2) | NOT NULL | - | Peak vibration RMS |
| `avg_pressure_psi` | NUMERIC(6,2) | NOT NULL | - | Mean hydraulic pressure |
| `total_power_kwh` | NUMERIC(8,4) | NOT NULL | - | Power consumed over interval (kWh) |
| `reading_count` | INT | NOT NULL | - | Number of raw sensor signals aggregated |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Lineage tracking pipeline batch ID |

---

### 2.5 `fact_maintenance_events`
* **Business Purpose**: Equipment maintenance history, technician workload, and preventive vs. reactive repair costs.
* **EXPLICIT GRAIN**: **One record per individual maintenance activity executed on a machine (`maintenance_id`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `maintenance_key` | BIGINT | NOT NULL | PK | Unique surrogate key |
| `maintenance_id` | UUID | NOT NULL | - | Source system maintenance event ID |
| `machine_key` | INT | NOT NULL | FK -> dim_machines | Machine surrogate key |
| `performed_date_key`| INT | NOT NULL | FK -> dim_date | Maintenance execution date (`YYYYMMDD`) |
| `maintenance_type` | VARCHAR(30) | NOT NULL | - | Type (PREVENTIVE, CORRECTIVE, EMERGENCY) |
| `cost_usd` | NUMERIC(10,2) | NOT NULL | - | Monetary cost of maintenance |
| `duration_hours` | NUMERIC(4,2) | NOT NULL | - | Duration of maintenance activity |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Pipeline batch ID |

---

### 2.6 `fact_support_tickets`
* **Business Purpose**: Support performance SLA tracking, issue root-cause metrics, and customer satisfaction analysis.
* **EXPLICIT GRAIN**: **One record per customer support ticket (`ticket_id`).**

| Column Name | Data Type | Nullable | Key | Business / Analytical Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `ticket_key` | BIGINT | NOT NULL | PK | Unique support ticket key |
| `ticket_id` | UUID | NOT NULL | - | Source system ticket identifier |
| `customer_key` | INT | NOT NULL | FK -> dim_customers | Requesting customer account key |
| `order_id` | UUID | NULL | - | Linked order ID (if applicable) |
| `created_date_key` | INT | NOT NULL | FK -> dim_date | Ticket opening date (`YYYYMMDD`) |
| `resolved_date_key`| INT | NULL | FK -> dim_date | Ticket resolution date (`YYYYMMDD`) |
| `priority` | VARCHAR(20) | NOT NULL | - | Ticket priority (LOW, MEDIUM, HIGH, URGENT) |
| `status` | VARCHAR(20) | NOT NULL | - | Ticket status (CLOSED, RESOLVED, OPEN) |
| `resolution_time_hours`| NUMERIC(6,2)| NULL | - | Total hours elapsed from opening to resolution |
| `satisfaction_score` | INT | NULL | - | Customer CSAT score (1 to 5) |
| `interaction_count` | INT | NOT NULL | - | Number of back-and-forth messages in thread |
| `etl_batch_id` | VARCHAR(50) | NOT NULL | - | Pipeline batch ID |

---

## 3. Slowly Changing Dimension (SCD) Strategy

### 3.1 SCD Type 1 (Overwrite)
* **Applied To**: `dim_products`, `dim_suppliers`, `dim_warehouses`.
* **Behavior**: Changes in attribute values (e.g., updating a product's list price or supplier address) overwrite existing records directly.
* **Justification**: Historical state tracking for minor attributes is unnecessary and overhead is avoided.

### 3.2 SCD Type 2 (Historical Tracking)
* **Applied To**: `dim_customers`, `dim_machines`.
* **Behavior**: Changes in key attributes (e.g., customer segment changes, machine relocation, credit limit changes) invalidate current record (`is_current = FALSE`, `valid_to = NOW()`) and insert a new row (`is_current = TRUE`, `valid_from = NOW()`).
* **Attributes**:
  * `surrogate_key` (PK INT)
  * `natural_key` (UUID)
  * `valid_from` (TIMESTAMPTZ)
  * `valid_to` (TIMESTAMPTZ)
  * `is_current` (BOOLEAN)

---

## 4. ML Feature Store Lineage & Analytical Datamarts

The analytical Gold tables serve directly as feature inputs for Machine Learning pipelines:

```text
  Gold Layer Tables                      ML Training Pipelines
┌──────────────────┐
│  fact_orders     ├──────┐
└──────────────────┘      │
┌──────────────────┐      ▼
│fact_support_tckts├───────────►  [Customer Churn Classifier]
└──────────────────┘      ▲       (Features: Recency, AOV, Open Ticket Ratio, CSAT)
┌──────────────────┐      │
│  dim_customers   ├──────┘
└──────────────────┘

┌──────────────────┐
│fact_order_items  ├──────┐
└──────────────────┘      ▼
┌──────────────────┐───────────►  [Demand Forecasting Engine]
│fact_inventory_dly│              (Features: 7d/30d Rolling Volume, Seasonality, SKU lead time)
└──────────────────┘

┌──────────────────┐
│fact_machine_telem├──────┐
└──────────────────┘      ▼
┌──────────────────┐───────────►  [IoT Telemetry Anomaly Detector]
│fact_mainten_evts │              (Features: 1-min Max Temp/Vibration Spikes, Hours Since Maintenance)
└──────────────────┘
```
