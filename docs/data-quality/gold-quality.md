# NexaCore Gold Data Quality & Governance Framework (Stage 4B Phase 5)

## Executive Summary

The Gold Data Quality Suite establishes continuous quality assurance, control totals reconciliation, domain profiling, and temporal integrity verification across the NexaCore Enterprise Data Warehouse (`analytics.*` schema).

### Overall Quality Scorecard

```json
{
  "overall_status": "PASSED",
  "tests_total": 55,
  "tests_passed": 55,
  "tests_failed": 0,
  "warnings": 0,
  "null_violations": 0,
  "referential_violations": 0,
  "business_rule_violations": 0,
  "temporal_violations": 0,
  "reconciliation_variances": 0,
  "orphan_records": 0,
  "freshness_status": "COMPLETED",
  "generated_at": "2026-08-18T00:39:24"
}
```

---

## 1. Table Grains & Key Uniqueness

| Table Name | Entity Grain | Business Key | Primary Surrogate Key | Expected Count | Observed Count | Grain Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dim_date` | 1 calendar date | `full_date` | `date_key` (INT) | 1,095 | 1,095 | **PASSED** |
| `dim_customer` | 1 active customer | `customer_id` (UUID) | `customer_id` | 1,000 | 1,000 | **PASSED** |
| `snp_customers` | 1 customer snapshot version | `customer_id` (UUID) | `customer_sk` (MD5) | 1,000 | 1,000 | **PASSED** |
| `dim_product` | 1 product item | `product_id` (UUID) | `product_id` | 100 | 100 | **PASSED** |
| `dim_supplier` | 1 supplier vendor | `supplier_id` (UUID) | `supplier_id` | 25 | 25 | **PASSED** |
| `dim_warehouse` | 1 distribution center | `warehouse_id` (UUID) | `warehouse_id` | 5 | 5 | **PASSED** |
| `dim_machine` | 1 plant machine | `machine_id` (UUID) | `machine_id` | 50 | 50 | **PASSED** |
| `fact_orders` | 1 purchase order | `order_id` (UUID) | `order_id` | 10,000 | 10,000 | **PASSED** |
| `fact_order_items` | 1 order line item | `order_item_id` (BIGINT) | `order_item_id` | 35,193 | 35,193 | **PASSED** |
| `fact_inventory_snapshot` | 1 product x warehouse snapshot | `inventory_id` (BIGINT) | `inventory_id` | 500 | 500 | **PASSED** |
| `fact_machine_telemetry` | 1 machine x 1-min rollup | `(machine_id, minute_timestamp)` | `telemetry_minute_key` | 29,800 | 29,800 | **PASSED** |
| `fact_maintenance_events` | 1 maintenance event | `maintenance_id` (UUID) | `maintenance_id` | 10 | 10 | **PASSED** |
| `fact_support_tickets` | 1 support ticket | `ticket_id` (UUID) | `ticket_id` | 2,500 | 2,500 | **PASSED** |

---

## 2. Referential Integrity & Foreign Key Audit

All foreign keys across Gold facts and dimensions were audited using automated `LEFT JOIN` outer queries.

- **`fact_orders.customer_id` -> `dim_customer.customer_id`**: 0 orphans (**PASSED**)
- **`fact_orders.date_key` -> `dim_date.date_key`**: 0 orphans (**PASSED**)
- **`fact_order_items.order_id` -> `fact_orders.order_id`**: 0 orphans (**PASSED**)
- **`fact_order_items.product_id` -> `dim_product.product_id`**: 0 orphans (**PASSED**)
- **`fact_inventory_snapshot.warehouse_id` -> `dim_warehouse.warehouse_id`**: 0 orphans (**PASSED**)
- **`fact_inventory_snapshot.product_id` -> `dim_product.product_id`**: 0 orphans (**PASSED**)
- **`fact_machine_telemetry.machine_id` -> `dim_machine.machine_id`**: 0 orphans (**PASSED**)
- **`fact_maintenance_events.machine_id` -> `dim_machine.machine_id`**: 0 orphans (**PASSED**)
- **`fact_support_tickets.customer_id` -> `dim_customer.customer_id`**: 0 orphans (**PASSED**)
- **`fact_support_tickets.customer_id` -> `snp_customers.customer_id`**: 0 orphans (**PASSED**)

**Total Orphan Records**: **0 across all 10 foreign key relationships**.

---

## 3. Business Rule Validation

1. **Order Total Amounts**: All 10,000 orders have `total_amount >= 0` ($0.00 negative order totals).
2. **Delivery Delay Days**: All derived delivery delays fall within valid boundaries (`-365` to `+365` days).
3. **Order Item Revenue Math**: 100% of line items satisfy `net_revenue = gross_revenue - discount_amount` with `quantity > 0` and `unit_price >= 0`.
4. **Inventory Quantity & Stockout Logic**: 100% of inventory records satisfy `quantity_available = quantity_on_hand - quantity_allocated` and stockout flags match `quantity_available < reorder_point`.
5. **Telemetry Domain Ranges**: All 29,800 rolled-up 1-minute telemetry records strictly obey physical boundaries:
   - Temperature: $0^\circ\text{C}$ to $150^\circ\text{C}$
   - Vibration: $0$ to $50\text{ RMS}$
   - Pressure: $0$ to $2,000\text{ PSI}$
   - Power: $0$ to $1,000\text{ kW}$
6. **Maintenance Downtime & Cost**: All maintenance costs and derived downtime hours are non-negative.
7. **Support Ticket Resolution & CSAT**: All resolution durations are non-negative, and all 1,748 linked CSAT scores fall within the legitimate 1 to 5 scale.

---

## 4. SCD Type 2 Customer Snapshot Integrity

> [!NOTE]
> **Dataset Limitation Note**: The customer source is a point-in-time snapshot and contains no genuine historical customer versions. Therefore, the `snp_customers` structure currently contains only Version 1 current active records and does not represent fabricated historical changes.

- **Source Customer Count**: 1,000
- **SCD2 Physical Row Count**: 1,000
- **Distinct `customer_id` Count**: 1,000
- **Active Record Count (`is_current = true`)**: 1,000
- **Customers with Multiple Active Versions**: 0
- **Customers with Zero Active Versions**: 0
- **Overlapping Validity Periods**: **0**

---

## 5. Cross-Fact Control Totals Reconciliation

| Metric | Silver Source Value | Gold Mart Value | Variance | Variance % | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`orders_count`** | 10,000 | 10,000 | 0 | 0.00% | **RECONCILED** |
| **`orders_revenue`** | $18,274,577.78 | $18,274,577.78 | $0.00 | 0.00% | **RECONCILED** |
| **`order_items_count`** | 35,193 | 35,193 | 0 | 0.00% | **RECONCILED** |
| **`order_items_quantity`** | 193,309 units | 193,309 units | 0 | 0.00% | **RECONCILED** |
| **`order_items_net_revenue`** | $18,274,577.78 | $18,274,577.78 | $0.00 | 0.00% | **RECONCILED** |
| **`order_items_discount`** | $1,056,586.32 | $1,056,586.32 | $0.00 | 0.00% | **RECONCILED** |
| **`inventory_on_hand`** | 184,520 units | 184,520 units | 0 | 0.00% | **RECONCILED** |
| **`inventory_allocated`** | 28,431 units | 28,431 units | 0 | 0.00% | **RECONCILED** |
| **`csat_survey_count`** | 1,748 | 1,748 | 0 | 0.00% | **RECONCILED** |
| **`csat_avg_score`** | 4.15 / 5.0 | 4.15 / 5.0 | 0.00 | 0.00% | **RECONCILED** |

---

## 6. Telemetry Quality & Aggregation Metrics

- **Raw Telemetry Events (Silver)**: 100,000 events (100% preserved in `source.machine_telemetry`)
- **Gold 1-Minute Aggregates**: 29,800 rows (`analytics.fact_machine_telemetry`)
- **Machines Represented**: 50 machines
- **Time Coverage**: 7 full days (`2026-01-01 00:00:00` to `2026-01-07 23:59:00`)
- **Aggregation Ratio**: **3.36:1** (100,000 raw events / 29,800 1-minute intervals)
- **Duplicate Keys**: 0
- **Missing Machine Key Gaps**: 0

---

## 7. Null Profile & Completeness

| Table.Column | Total Rows | Null Count | Null % | Classification | Quality Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fact_orders.order_id` | 10,000 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_orders.customer_id` | 10,000 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_orders.total_amount` | 10,000 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_orders.promised_delivery_date` | 10,000 | 0 | 0.00% | OPTIONAL | **PASSED** |
| `fact_order_items.order_item_id` | 35,193 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_order_items.gross_revenue` | 35,193 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_order_items.net_revenue` | 35,193 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_support_tickets.ticket_id` | 2,500 | 0 | 0.00% | REQUIRED | **PASSED** |
| `fact_support_tickets.resolved_at` | 2,500 | 385 | 15.40% | CONDITIONAL | **PASSED** |
| `fact_support_tickets.csat_score` | 2,500 | 752 | 30.08% | CONDITIONAL | **PASSED** |

---

## 8. Domain & Numeric Range Profiling

| Table.Column | Min | Max | Average | Zero Count | Negative Count | Null Count |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `fact_orders.total_amount` | $15.50 | $12,450.00 | $1,827.46 | 0 | 0 | 0 |
| `fact_order_items.quantity` | 1 | 20 | 5.49 | 0 | 0 | 0 |
| `fact_order_items.net_revenue` | $4.50 | $4,850.00 | $519.27 | 0 | 0 | 0 |
| `fact_order_items.discount_amount` | $0.00 | $450.00 | $30.02 | 8,421 | 0 | 0 |
| `fact_inventory_snapshot.quantity_available` | 0 | 950 | 312.18 | 12 | 0 | 0 |
| `fact_machine_telemetry.avg_temperature_c` | 42.10 | 98.40 | 68.25 | 0 | 0 | 0 |
| `fact_machine_telemetry.avg_vibration_rms` | 0.12 | 4.85 | 1.84 | 0 | 0 | 0 |
| `fact_support_tickets.resolution_time_hours` | 0.50 | 168.00 | 28.45 | 0 | 0 | 0 |
| `fact_support_tickets.csat_score` | 1 | 5 | 4.15 | 0 | 0 | 752 |

---

## 9. Pipeline Freshness & Readiness

- **Latest Batch Execution ID**: `batch_20260818_003907_fe0357`
- **Execution Status**: `COMPLETED`
- **Total Ingestion Duration**: 10.59 seconds
- **Quarantined Records**: **0**
- **Idempotent Checkpoint Replays**: 0
- **Freshness SLA**: **COMPLETED & READY**
