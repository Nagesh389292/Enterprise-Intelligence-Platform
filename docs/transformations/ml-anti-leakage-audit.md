# Stage 4B Phase 7 — ML Feature Marts Anti-Leakage Audit Report

**Platform:** NexaCore Enterprise Intelligence Platform  
**Audit Executed:** 2026-08-18  
**Audit Status:** 🟢 **PASSED (13/13 Checks Passed, 0 Failures)**  
**Auditor Engine:** `scripts/ml_anti_leakage_audit.py`  
**Report Artifact:** [`docs/data-quality/ml_anti_leakage_report.json`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/docs/data-quality/ml_anti_leakage_report.json)

---

## 1. Executive Summary

Data-quality tests (such as `not_null`, `unique`, and `relationships`) verify structural and referential integrity, but they do not prove temporal anti-leakage compliance for Machine Learning. Temporal leakage occurs when information from after the prediction cutoff date or target window is inadvertently included in input feature engineering, producing artificially high model evaluation metrics that collapse in real-world deployment.

To guarantee production-grade ML readiness, a dedicated automated anti-leakage audit was conducted across all **4 Gold ML Feature Marts** in PostgreSQL:
1. **`ml_customer_churn_features`** (1,000 rows — Churn Prediction)
2. **`ml_demand_forecasting_daily`** (18,100 rows — Daily Demand Forecasting)
3. **`ml_inventory_stockout_risk`** (500 rows — Inventory Classification)
4. **`ml_machine_telemetry_features`** (29,800 rows — Real-Time IoT Anomaly Detection)

All **13 audit checks passed with zero leakage defects detected**.

---

## 2. Feature Mart Anti-Leakage Audit Scorecard

| Feature Mart | Objective | Grain | Cutoff / Window Constraint | Audit Checks | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **`ml_customer_churn_features`** | Customer Churn | 1 row / customer (1,000) | `feature_cutoff_date = '2026-05-01'`, Target window `(cutoff, cutoff + 60d]` | 4 / 4 | 🟢 PASS |
| **`ml_demand_forecasting_daily`** | Demand Forecast | 1 row / prod / date (18,100) | `ROWS BETWEEN ... PRECEDING AND 1 PRECEDING` for lag & rolling avg | 4 / 4 | 🟢 PASS |
| **`ml_inventory_stockout_risk`** | Stockout Risk | 1 row / inventory item (500) | `quantity_available < reorder_point` target vs predictive features | 2 / 2 | 🟢 PASS |
| **`ml_machine_telemetry_features`** | IoT Anomaly | 1 row / machine / min (29,800) | `ROWS BETWEEN 10 PRECEDING AND CURRENT ROW` backward window | 3 / 3 | 🟢 PASS |

---

## 3. Detailed Audit Evidence by Feature Mart

### 3.1 `ml_customer_churn_features`
* **Business Objective:** Predict customer churn over a 60-day window following cutoff.
* **Temporal Cutoff Date:** `2026-05-01` (strictly uniform across all 1,000 customer rows).
* **Empirical Verification:**
  - **Check `churn_01_uniform_cutoff` (PASS):** Cutoff date `2026-05-01` verified across all rows.
  - **Check `churn_02_pre_cutoff_features` (PASS):** 0 orders with `order_timestamp > '2026-05-01'` were included in pre-cutoff feature aggregations (`total_orders_to_cutoff`, `total_spend_to_cutoff`, `recency_days_at_cutoff`).
  - **Check `churn_03_target_window_isolation` (PASS):** Target observation window starts on `2026-05-02` (min date) and ends on `2026-06-30` (max date).
  - **Check `churn_04_zero_feature_target_overlap` (PASS):** Proven **0 temporal overlap** between feature calculation window ($\le \text{2026-05-01}$) and target observation window ($> \text{2026-05-01}$).

### 3.2 `ml_demand_forecasting_daily`
* **Business Objective:** Forecast product demand (`units_sold_target`) per product per date.
* **Temporal Window Constraint:** Lag features (`lag_7`, `lag_14`) and rolling averages (7-day, 30-day) must exclude the target date $T$.
* **Empirical Verification:**
  - **Check `demand_01_lag_7_verification` (PASS):** `lag_7_units_sold` on date $T$ matches `units_sold_target` on date $T - 7$ with 0 mismatches.
  - **Check `demand_02_lag_14_verification` (PASS):** `lag_14_units_sold` on date $T$ matches `units_sold_target` on date $T - 14$ with 0 mismatches.
  - **Check `demand_03_rolling_avg_excludes_current_target` (PASS):** `rolling_7_day_avg_units` uses `ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING`, strictly excluding target date $T$ with 0 variances.
  - **Check `demand_04_target_feature_isolation` (PASS):** Proven `units_sold_target` is strictly isolated from all input features.

### 3.3 `ml_inventory_stockout_risk`
* **Business Objective:** Classify inventory items at risk of stockout.
* **Feature Separation & Target Definition:**
  - Target label: `stockout_risk_flag_target = 1` if `quantity_available < reorder_point` else `0`.
* **Empirical Verification:**
  - **Check `inventory_01_target_definition` (PASS):** 100% logic match with 0 invalid label assignments.
  - **Check `inventory_02_feature_target_separation` (PASS):** Verified target distribution (87 high-risk items / 17.4%). Documented feature separation: `quantity_available` is the target state, whereas `quantity_on_hand`, `quantity_allocated`, `reorder_quantity`, `days_of_supply`, `unit_cost`, and `unit_price` form the predictive feature space.

### 3.4 `ml_machine_telemetry_features`
* **Business Objective:** Real-time IoT machine health monitoring and anomaly severity scoring.
* **Temporal Window Constraint:** 10-minute rolling averages must be strictly backward-looking.
* **Empirical Verification:**
  - **Check `telemetry_01_rolling_window_backward_looking` (PASS):** `rolling_10min_avg_temp` uses `ROWS BETWEEN 10 PRECEDING AND CURRENT ROW`, containing 0 `FOLLOWING` (future) sensor readings.
  - **Check `telemetry_02_first_row_boundary_correctness` (PASS):** Row 1 boundary condition verified (0 errors).
  - **Check `telemetry_03_contemporaneous_anomaly_score` (PASS):** `anomaly_severity_score` evaluates sensor health at minute $t$ with 0 forward sensor dependencies.

---

## 4. Automation & Governance Integration

The automated auditor script [`scripts/ml_anti_leakage_audit.py`](file:///c:/Users/NAGESH%20REDDY/Desktop/Data%20Analytics/enterprise-intelligence-platform/scripts/ml_anti_leakage_audit.py) has been integrated into the NexaCore pipeline validation suite. Any future dbt model updates or feature additions will automatically trigger anti-leakage assertion checks prior to model deployment.
