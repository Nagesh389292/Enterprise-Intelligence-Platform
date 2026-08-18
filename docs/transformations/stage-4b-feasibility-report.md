# Stage 4B Pre-Flight — Gold Implementation Feasibility & Empirical Data Profiling Report
### NexaCore Enterprise Intelligence Platform

---

## 📌 Executive Summary

This report presents the empirical data profiling, schema validation, and feasibility adjustments for **Stage 4B (Gold Star Schema Transformations)** of the **NexaCore Enterprise Intelligence Platform**, executed directly against the live PostgreSQL Silver dataset (`source.*` schema on port `5433`).

Pursuant to the pre-flight verification directive, **all proposed Gold transformations were audited against empirical database evidence prior to writing dbt models or modifying database schemas**.

Four critical architectural corrections were incorporated based on direct PostgreSQL queries:
1. **Truthful Inventory Grain**: Replaced fabricated 180-day daily inventory series with source-supported **`fact_inventory_snapshot`** (1 row per product × warehouse inventory snapshot).
2. **Derived Delivery Timestamp Labeling**: `source.orders` does NOT contain `actual_delivery_date`. Delivery delay calculations using synthetic offsets are explicitly labeled as **`DERIVED/SYNTHETIC`** (`derived_actual_delivery_date`).
3. **Independent Supplier Dimension**: Confirmed `products` and `inventory` tables have **zero foreign keys** linking to `suppliers`. `dim_supplier` is maintained as a standalone dimension; no fake supplier relationships will be injected into facts.
4. **Resolved Machine Count**: Direct database count confirmed **50 machines** (`SELECT COUNT(*) FROM source.machines;`), correcting the earlier report notation.

---

## 1. Empirical PostgreSQL Database Audit Results

Inspection executed via `scripts/verify_stage4b_corrections.py` over PostgreSQL database `nexacore_dw` on port `5433`:

```json
{
  "machine_count": 50,
  "has_supplier_in_products": false,
  "has_supplier_in_inventory": false,
  "inventory_stats": {
    "min_count_date": "2026-06-30 00:00:00+00:00",
    "max_count_date": "2026-06-30 00:00:00+00:00",
    "distinct_dates": 1,
    "total_inventory_records": 500
  },
  "has_actual_delivery_date": false
}
```

### Source Schema & Row Count Summary:
| Source Table (`source.*`) | Entity Tier | Verified Row Count | Foreign Keys Identified | Key Adjustments |
| :--- | :--- | :--- | :--- | :--- |
| `customer_segments` | Reference | 4 | None | Standard lookup |
| `customers` | Core | 1,000 | `segment_id` → `customer_segments` | Initial SCD2 snapshot version |
| `customer_addresses` | Transactional | 1,000 | `customer_id` → `customers` | Primary shipping location |
| `product_categories` | Reference | 8 | `parent_category_id` → self | Category hierarchy |
| `products` | Core | 100 | `category_id` → `product_categories` | NO `supplier_id` present |
| `orders` | Transactional | 10,000 | `customer_id` → `customers`, `shipping_address_id` → `customer_addresses` | NO `actual_delivery_date` present |
| `order_items` | Transactional | 35,193 | `order_id` → `orders`, `product_id` → `products` | Line-item detail |
| `suppliers` | Reference | 25 | None | Standalone dimension |
| `warehouses` | Reference | 5 | None | Regional distribution hubs |
| `inventory` | Supply Chain | 500 | `warehouse_id` → `warehouses`, `product_id` → `products` | NO `supplier_id`, 1 snapshot date (`2026-06-30`) |
| `machine_types` | Reference | 6 | None | Telemetry threshold specifications |
| `machines` | Core | 50 | `machine_type_id` → `machine_types`, `warehouse_id` → `warehouses` | Exactly 50 machines verified |
| `machine_telemetry` | Operations | 100,000 | `machine_id` → `machines` | 1-min sensor events |
| `maintenance_events` | Operations | 10 | `machine_id` → `machines` | Servicing records |
| `failure_events` | Operations | 3 | `machine_id` → `machines` | Machine failure logs |
| `support_tickets` | Support | 2,500 | `customer_id` → `customers`, `order_id` → `orders` | Service requests |
| `customer_satisfaction` | Support | 1,748 | `ticket_id` → `support_tickets` | CSAT survey scores |

---

## 2. Updated Gold Star Schema Feasibility Matrix

| Gold Table (`analytics.*`) | Target Grain | Feasibility Status | Truthful Data Mapping Strategy |
| :--- | :--- | :--- | :--- |
| `dim_date` | 1 row per calendar day | `FEASIBLE` | System generated (`2025-01-01` to `2027-12-31`) |
| `dim_customer` | 1 row per customer version | `FEASIBLE (SCD1/SCD2)` | Initial snapshot version 1; future updates trigger dbt snapshots |
| `dim_product` | 1 row per product | `FEASIBLE (SCD1)` | Joins `products` + `product_categories` |
| `dim_supplier` | 1 row per supplier | `FEASIBLE (SCD1)` | Standalone dimension; no forced joins to inventory/products |
| `dim_warehouse` | 1 row per warehouse | `FEASIBLE (SCD1)` | Includes regional distribution metadata |
| `dim_machine` | 1 row per machine | `FEASIBLE (SCD1)` | Verified exactly 50 machines |
| `fact_orders` | 1 row per order | `FEASIBLE` | `delivery_delay_days` calculated using explicitly labeled `derived_actual_delivery_date` |
| `fact_order_items` | 1 row per line item | `FEASIBLE` | Gross/net revenue and margin (`net_revenue - quantity * unit_cost`) |
| `fact_inventory_snapshot` | 1 row per product × WH snapshot | `FEASIBLE` | **Truthful snapshot grain (500 rows)**; no fabricated 180-day history |
| `fact_machine_telemetry` | 1 row per machine × 1-min aggregate | `FEASIBLE` | Aggregates 100K raw telemetry events to ~29.8K 1-min rollups |
| `fact_maintenance_events`| 1 row per maintenance event | `FEASIBLE` | Servicing costs and downtime tracking |
| `fact_support_tickets` | 1 row per support ticket | `FEASIBLE` | Ticket resolution hours and linked CSAT survey score |

---

## 3. Pre-Implementation Architectural Corrections Detail

### 3.1 Inventory Fact Grain Correction
* **Problem**: Proposed `fact_inventory_daily` (1 row per product × warehouse × day) would require fabricating 180 days of non-existent daily inventory observations from 500 snapshot rows.
* **Correction**: Implement **`fact_inventory_snapshot`** at grain **1 row per product × warehouse inventory snapshot** (500 rows). Stockout risk metrics will be computed directly against this observed snapshot. If a daily model is created later, it will be clearly documented as an as-of/forward-fill model.

### 3.2 Delivery Timestamp & Delay Labeling
* **Problem**: `source.orders` contains `order_timestamp` and `promised_delivery_date`, but no `actual_delivery_date`.
* **Correction**: The derived delivery timestamp is calculated as `order_timestamp + synthetic_delivery_offset` and stored in column **`derived_actual_delivery_date`**. All dbt documentation will explicitly state that this is a synthetic derived metric, ensuring full data audit transparency.

### 3.3 Supplier Dimension Isolation
* **Problem**: The original design planned to join `dim_supplier` to inventory and facts.
* **Correction**: Database foreign key audit confirmed `products` and `inventory` have **no supplier foreign key**. `dim_supplier` will be implemented as a standalone dimension. Supplier metrics will not be forcibly joined to inventory or facts.

### 3.4 Machine Count Standardization
* **Problem**: Feasibility text contained an inconsistent reference to "5 machines".
* **Correction**: Direct SQL query `SELECT COUNT(*) FROM source.machines;` confirmed **50 machines**. All documentation and test assertions standardized to **50 machines**.

---

## 4. Control Totals Baseline for Silver-to-Gold Reconciliation

The following baseline metrics from Silver (`source.*`) will be reconciled against Gold (`analytics.*`) post-dbt execution:

| Domain | Source Baseline Metric | Exact Baseline Value | Target Gold Model | Expected Reconciled Variance |
| :--- | :--- | :--- | :--- | :--- |
| Orders | Total Order Count | **10,000 orders** | `fact_orders` | `0` (Exact Match) |
| Revenue | Sum of `total_amount` | **$18,274,577.78** | `fact_orders` | `0.00` (Exact Match) |
| Order Line Items | Total Line Items | **35,193 items** | `fact_order_items` | `0` (Exact Match) |
| Order Quantity | Sum of `quantity` | **193,309 units** | `fact_order_items` | `0` (Exact Match) |
| Order Net Revenue | Sum of `total_price` | **$18,274,577.78** | `fact_order_items` | `0.00` (Exact Match) |
| Order Discounts | Sum of `discount_amount` | **$1,056,586.32** | `fact_order_items` | `0.00` (Exact Match) |
| Inventory Stock | Sum of `quantity_on_hand` | **184,520 units** | `fact_inventory_snapshot` | `0` (Exact Match) |
| Inventory Allocated | Sum of `quantity_allocated` | **28,431 units** | `fact_inventory_snapshot` | `0` (Exact Match) |
| Support CSAT | Total CSAT Surveys | **1,748 surveys** | `fact_support_tickets` | `0` (Exact Match) |
| Average CSAT Score | Mean CSAT Rating | **4.15 / 5.0** | `fact_support_tickets` | `0.00` (Exact Match) |

---

## 5. dbt Environment & Technical Readiness Check

The dbt execution environment in project virtual environment `.\venv` was audited and prepared:

* **Python Version**: `3.13.5`
* **`dbt-core` Installed**: `1.12.2` (Authoritative)
* **`dbt-postgres` Installed**: `1.11.0` (Authoritative)
* **PostgreSQL Engine**: Running on `127.0.0.1:5433`, database `nexacore_dw`. Connectivity verified.
* **Execution Strategy**: PostgreSQL + dbt Core for Gold transformations. PySpark is retained for future scale pathways and not used for this ~152K record development dataset.

---

## 🛑 Scope Guard Status & Environment Report
- **Python**: 3.13.5
- **dbt-core**: 1.12.2
- **dbt-postgres**: 1.11.0
- **PostgreSQL Connectivity**: Verified on `127.0.0.1:5433`
- **Gold Models Written**: **0** (Stopped per instructions before creating the first Gold model)
