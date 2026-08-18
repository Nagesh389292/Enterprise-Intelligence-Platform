# NexaCore ML Feature Marts & Anti-Leakage Specification (Stage 4B Phase 7)

## Executive Summary

Stage 4B Phase 7 builds **4 production-grade Machine Learning Feature Marts** in the PostgreSQL Gold layer (`analytics.ml_*`). Each feature mart is engineered to enforce **strict temporal anti-leakage constraints**, aligning features strictly prior to cutoff dates or utilizing backward-looking rolling windows.

All 4 ML feature marts are fully built, tested with 16 automated dbt data quality tests (**140/140 total passing tests in dbt**), and reconciled against Silver/Gold control totals.

---

## 1. Feature Mart Architecture & Summary Matrix

| Feature Mart Table | Business ML Use Case | Entity Grain | Total Rows | Target Variable | Class / Value Profile | Anti-Leakage Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ml_customer_churn_features` | Customer Churn Prediction | 1 Customer | 1,000 | `is_churned_target` | 82 churned (8.2%), 918 active (91.8%) | Features bounded by `feature_cutoff_date` (`2026-05-01`). Target observed post-cutoff (60 days). |
| `ml_demand_forecasting_daily` | Product Demand Forecasting | 1 Product $\times$ 1 Date | 18,100 | `units_sold_target` | 193,309 total units sold across 181 dates | Lag features (7d, 14d) and rolling window averages (7d, 30d) strictly use `PRECEDING` dates. |
| `ml_inventory_stockout_risk` | Stockout Risk Classification | 1 Product $\times$ 1 Warehouse | 500 | `stockout_risk_flag_target` | 87 high risk (17.4%), 413 safe (82.6%) | Snapshot state evaluation (`quantity_available < reorder_point`). |
| `ml_machine_telemetry_features` | IoT Anomaly Detection | 1 Machine $\times$ 1 Minute | 29,800 | `anomaly_severity_score` | 50 machines over 7 full days (29,800 intervals) | 10-minute rolling feature windows use `ROWS BETWEEN 10 PRECEDING AND CURRENT ROW`. |

---

## 2. Detailed Mart Specifications

### 2.1 Customer Churn Feature Mart (`analytics.ml_customer_churn_features`)

- **Table Name**: `analytics.ml_customer_churn_features`
- **Grain**: 1 row per customer (1,000 rows)
- **Cutoff Date**: `2026-05-01`
- **Temporal Anti-Leakage Boundary**:
  - `total_orders_to_cutoff`, `total_spend_to_cutoff`, `avg_order_value_to_cutoff`, `recency_days_at_cutoff`, `total_support_tickets_to_cutoff`, and `avg_csat_score_to_cutoff` are calculated exclusively on events $\le \text{2026-05-01}$.
  - `is_churned_target` evaluates whether the customer placed zero orders between `2026-05-01` and `2026-06-30` (60-day observation window).

```sql
SELECT
    customer_id,
    segment_name,
    primary_state_province,
    account_tenure_days,
    total_orders_to_cutoff,
    total_spend_to_cutoff,
    avg_order_value_to_cutoff,
    recency_days_at_cutoff,
    total_support_tickets_to_cutoff,
    avg_csat_score_to_cutoff,
    feature_cutoff_date,
    is_churned_target
FROM analytics.ml_customer_churn_features;
```

---

### 2.2 Demand Forecasting Feature Mart (`analytics.ml_demand_forecasting_daily`)

- **Table Name**: `analytics.ml_demand_forecasting_daily`
- **Grain**: 1 row per product $\times$ 1 calendar date (100 products $\times$ 181 dates = 18,100 rows)
- **Reconciliation Control Total**: Sum of `units_sold_target` = **193,309 units** (100% exact match with Silver `order_items`)
- **Temporal Anti-Leakage Boundary**:
  - `lag_7_units_sold`: `LAG(units_sold_target, 7) OVER (PARTITION BY product_id ORDER BY full_date)`
  - `lag_14_units_sold`: `LAG(units_sold_target, 14) OVER (PARTITION BY product_id ORDER BY full_date)`
  - `rolling_7_day_avg_units`: `ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING`
  - `rolling_30_day_avg_units`: `ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING`

---

### 2.3 Inventory Stockout Risk Feature Mart (`analytics.ml_inventory_stockout_risk`)

- **Table Name**: `analytics.ml_inventory_stockout_risk`
- **Grain**: 1 row per product $\times$ warehouse inventory item (500 snapshot rows)
- **Class Profile**:
  - Stockout Risk (`stockout_risk_flag_target = 1`): **87 items (17.4%)**
  - Adequate Stock (`stockout_risk_flag_target = 0`): **413 items (82.6%)**
  - Average Days of Supply: **48.51 days**

---

### 2.4 Machine Telemetry Anomaly Feature Mart (`analytics.ml_machine_telemetry_features`)

- **Table Name**: `analytics.ml_machine_telemetry_features`
- **Grain**: 1 row per machine $\times$ 1-minute interval (29,800 rows across 50 machines over 7 days)
- **Features & Anomaly Metrics**:
  - `avg_temperature_c`, `max_temperature_c`, `temp_spread`
  - `avg_vibration_rms`, `max_vibration_rms`
  - `avg_pressure_psi`, `avg_power_kw`
  - `rolling_10min_avg_temp`, `rolling_10min_avg_vib` (`ROWS BETWEEN 10 PRECEDING AND CURRENT ROW`)
  - `anomaly_severity_score`: Weighted anomaly flag based on physical thresholds ($T > 85^\circ\text{C}$, $\text{Vib} > 3.5\text{ RMS}$, $P > 1500\text{ PSI}$).

---

## 3. Data Quality & Test Coverage

All ML feature marts are registered in `dbt/models/marts/ml/ml_schema.yml` with 16 automated tests covering:
- Primary key uniqueness & non-null integrity.
- Foreign key relationships to `dim_customer`, `dim_product`, `dim_warehouse`, `dim_date`, and `dim_machine`.
- Non-null target labels across all 4 marts.

```text
dbt build result: PASS=140 WARN=0 ERROR=0 TOTAL=140
```
