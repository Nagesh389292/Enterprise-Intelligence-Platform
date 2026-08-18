# ML Feature Lineage & Anti-Leakage Temporal Cutoffs
### NexaCore Enterprise Intelligence Platform

---

## 📌 ML Feature Matrix Mapping

To train predictive ML models without data leakage, feature definitions are derived directly from Gold star-schema tables with explicit **Temporal Cutoff Windows ($T_{\text{feature}} < T_{\text{prediction}}$)**.

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                           TEMPORAL CUTOFF TIMELINE                          │
 │                                                                             │
 │ ◄──────────────── Feature Window (30d / 90d History) ─────────►│            │
 │ Historical Data (Orders, Telemetry, CSAT, Stock)                │ Cutoff $T$  │ Target Window (Next 30d)
 │                                                                 │            │ (Churn / Failure Event)
 └─────────────────────────────────────────────────────────────────┴────────────┴─────────────────────────►
```

---

## 1. Feature Lineage & Temporal Cutoff Specifications

### 1.1 Use Case 1: Customer Churn Prediction (Binary Classification)
* **Target Variable**: `is_churned` (1 if no order placed in 90 days following Cutoff $T$, 0 otherwise)
* **Feature Cutoff**: All metrics computed using data strictly before Cutoff $T$.

| Feature Name | Source Gold Table | Aggregation Logic | Temporal Cutoff |
| :--- | :--- | :--- | :--- |
| `recency_days` | `fact_orders` | Days between Cutoff $T$ and last order date | $t \le T$ |
| `frequency_90d` | `fact_orders` | Count of orders placed in $T - 90\text{d} \le t \le T$ | $T - 90\text{d} \le t \le T$ |
| `monetary_90d` | `fact_orders` | Total order revenue in $T - 90\text{d} \le t \le T$ | $T - 90\text{d} \le t \le T$ |
| `avg_csat_score` | `fact_support_tickets` | Average survey score before $T$ | $t \le T$ |
| `urgent_ticket_count`| `fact_support_tickets` | Count of URGENT priority tickets in $T - 30\text{d} \le t \le T$ | $T - 30\text{d} \le t \le T$ |

---

### 1.2 Use Case 2: Product Demand Forecasting (Time Series Regression)
* **Target Variable**: `next_7d_unit_sales` (Sum of order item quantity in 7 days following Cutoff $T$)

| Feature Name | Source Gold Table | Aggregation Logic | Temporal Cutoff |
| :--- | :--- | :--- | :--- |
| `unit_sales_lag_7d` | `fact_order_items` | Total sales quantity in $T - 7\text{d} \le t \le T$ | $T - 7\text{d} \le t \le T$ |
| `unit_sales_lag_30d`| `fact_order_items` | Total sales quantity in $T - 30\text{d} \le t \le T$ | $T - 30\text{d} \le t \le T$ |
| `sales_momentum_ratio`| `fact_order_items` | $\text{sales\_lag\_7d} / (\text{sales\_lag\_30d} / 4.28)$ | $t \le T$ |
| `unit_price` | `dim_product` | Current price at $T$ | $t = T$ |

---

### 1.3 Use Case 3: Inventory Stockout Risk (Binary Classification)
* **Target Variable**: `will_stockout_7d` (1 if `quantity_on_hand` reaches 0 within 7 days after Cutoff $T$)

| Feature Name | Source Gold Table | Aggregation Logic | Temporal Cutoff |
| :--- | :--- | :--- | :--- |
| `quantity_available` | `fact_inventory_daily` | Current available inventory at Cutoff $T$ | $t = T$ |
| `days_of_supply` | `fact_inventory_daily` | Computed days of supply at $T$ | $t = T$ |
| `lead_time_days` | `dim_supplier` | Supplier lead time at $T$ | $t = T$ |

---

### 1.4 Use Case 4 & 5: Machine Anomaly & Failure Prediction
* **Target Variable**: `will_fail_24h` (1 if `fact_failure_events` records breakdown within 24 hours after Cutoff $T$)

| Feature Name | Source Gold Table | Aggregation Logic | Temporal Cutoff |
| :--- | :--- | :--- | :--- |
| `avg_temp_1h` | `fact_machine_telemetry` | Mean temperature in $T - 1\text{h} \le t \le T$ | $T - 1\text{h} \le t \le T$ |
| `temp_spike_ratio` | `fact_machine_telemetry` | $\text{max\_temp\_1h} / \text{avg\_temp\_24h}$ | $T - 24\text{h} \le t \le T$ |
| `avg_vibration_1h` | `fact_machine_telemetry` | Mean RMS vibration in $T - 1\text{h} \le t \le T$ | $T - 1\text{h} \le t \le T$ |
| `operating_days` | `dim_machine` | Days since installation date at Cutoff $T$ | $t = T$ |
| `days_since_maintenance`| `fact_maintenance_events`| Days between last preventive maintenance and Cutoff $T$ | $t \le T$ |
