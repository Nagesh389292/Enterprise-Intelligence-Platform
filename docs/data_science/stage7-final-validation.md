# Stage 7 — Final Validation Scorecard & Execution Report
# NexaCore Enterprise Intelligence Platform

**Validation Date:** 2026-08-18  
**Execution Environment:** Python 3.13 Virtual Environment (`venv`), PostgreSQL `nexacore_dw`  
**Execution Status:** 🟢 **STAGE 7 IS OFFICIALLY COMPLETE & FULLY VALIDATED**  
**Stage 8 Status:** 🛑 **STAGE 8 HAS NOT BEEN STARTED. AWAITING USER APPROVAL.**  

---

## 1. Notebook Execution Scorecard

All 6 notebooks were executed end-to-end against the live PostgreSQL database via `scripts/run_stage7_notebooks.py`. Every `.ipynb` file in `notebooks/` contains embedded cell outputs, print statements, and matplotlib figures.

| Notebook | File | Status | Duration | Control Checks | Stat Tests Executed | Outputs Embedded |
|---|---|---|---|---|---|---|
| **01 Executive Overview** | `notebooks/01_eda_executive_overview.ipynb` | 🟢 PASS | 16.00s | 9 / 9 PASS | 3 | ✅ Yes |
| **02 Customer Churn** | `notebooks/02_eda_customer_churn.ipynb` | 🟢 PASS | 14.15s | 3 / 3 PASS | 11 | ✅ Yes |
| **03 Demand Forecasting** | `notebooks/03_eda_demand_forecasting.ipynb` | 🟢 PASS | 10.52s | 3 / 3 PASS | 23 | ✅ Yes |
| **04 Inventory Stockout** | `notebooks/04_eda_inventory_stockout.ipynb` | 🟢 PASS | 8.70s | 3 / 3 PASS | 8 | ✅ Yes |
| **05 Machine Anomaly** | `notebooks/05_eda_machine_anomaly.ipynb` | 🟢 PASS | 25.91s | 3 / 3 PASS | 7 | ✅ Yes |
| **06 Statistical Testing** | `notebooks/06_statistical_testing.ipynb` | 🟢 PASS | 7.76s | 2 / 2 PASS | 6 | ✅ Yes |
| **TOTALS** | **6 / 6 Notebooks** | 🟢 **PASS** | **83.04s** | **23 / 23 PASS** | **58 Tests** | **0 Unexecuted** |

---

## 2. Control Total Reconciliation Table

All figures extracted in Stage 7 were reconciled against the canonical PostgreSQL control totals.

| Area | Computed Value | Canonical Control Target | Drift | Status |
|---|---|---|---|---|
| **Net Revenue** | $77,237,960.93 | $77,237,960.93 | $0.00 | ✅ Exact Match |
| **Total Orders** | 10,000 | 10,000 | 0 | ✅ Exact Match |
| **Order Items** | 35,193 | 35,193 | 0 | ✅ Exact Match |
| **Unique Customers** | 1,000 | 1,000 | 0 | ✅ Exact Match |
| **Avg CSAT Score** | 3.38 | 3.38 | 0.00 | ✅ Exact Match |
| **Inventory On Hand** | 210,174 units | 210,174 units | 0 | ✅ Exact Match |
| **Low Stock Items** | 85 items | 85 items | 0 | ✅ Exact Match |
| **Fleet Machine Count** | 50 machines | 50 machines | 0 | ✅ Exact Match |
| **Telemetry Records** | 100,000 records | 100,000 records | 0 | ✅ Exact Match |

---

## 3. Empirical Findings Summary

1. **Customer Churn (`02_eda_customer_churn`):**
   - **Churn Rate:** **4.40%** (44 churned vs 956 retained). Extreme 21.73 : 1 imbalance ratio.
   - **Baseline Logistic Regression:** **AUC = 0.4396 ± 0.0278** (Train AUC = 0.7013). Linear Logistic Regression heavily overfits and performs worse than random guessing (0.5000) on standard unweighted loss. Non-linear tree boosting (XGBoost) with `scale_pos_weight` and threshold optimization (< 0.30) is required for Stage 8.
2. **Demand Forecasting (`03_eda_demand_forecasting`):**
   - **Data Grain:** 18,100 daily SKU records across 100 products (181 days, Jan-Jun 2026).
   - **Predictors:** `rolling_7_day_avg_units` (**r = 0.6473**, p < 0.001), `lag_7_units_sold` (**r = 0.4752**, p < 0.001), `lag_14_units_sold` (**r = 0.4625**, p < 0.001).
   - **Baseline Models:** Rolling 7-day average (**MAPE = 90.61%**) outperforms Naïve Lag-7 persistence (**MAPE = 116.49%**) by **25.88% MAPE points**.
3. **Inventory Stockout Risk (`04_eda_inventory_stockout`):**
   - **Stockout Prevalence:** **21.25%** (85 at-risk items / 315 adequate).
   - **Separability:** Derived `buffer_ratio` and `safety_margin` show large, statistically significant separation (**Mann-Whitney U p = 0.000000 *** **, effect size = **-0.88**). Baseline Logistic Regression achieves **0.9993 AUC**.
   - **Limitation:** 400-row point-in-time snapshot. Interpretable linear / decision tree models are optimal; XGBoost is unnecessary.
4. **Machine Telemetry Anomaly (`05_eda_machine_anomaly`):**
   - **Signal Distribution:** Non-normal signals (`avg_temperature_c` p < 0.001, `avg_vibration_rms` p < 0.001). Kruskal-Wallis tests confirm statistically significant baseline shifts across machine types (**H = 142.04**, p < 0.001).
   - **Model:** Isolation Forest @ 5% contamination detects 5,000 anomalous minutes. Per-machine-type Z-score normalization is mandatory before Stage 8 modeling.
   - **Limitation:** Only 3 maintenance event records exist; supervised learning is mathematically impossible. Unsupervised anomaly detection is the strictly valid framing.

---

## 4. Leakage-Risk Matrix

| Feature / Dimension | Risk Level | Audit Result & Temporal Boundary Rules |
|---|---|---|
| `recency_days_at_cutoff` | LOW | Calculated strictly prior to cutoff date (**2026-05-01**) |
| `total_orders_to_cutoff` | LOW | Aggregate of historical orders up to cutoff date |
| `total_spend_to_cutoff` | LOW | Aggregate of historical revenue up to cutoff date |
| `lag_7_units_sold` | LOW | Strictly $t-7$ relative to target day $t$ |
| `rolling_7_day_avg_units` | LOW | Moving window over $[t-7, t-1]$ |
| `is_churned_target` | TARGET | Defined strictly on post-cutoff window (**2026-05-02** to **2026-07-31**) |
| `stockout_risk_flag_target` | TARGET | Cross-sectional target flag on snapshot date (**2026-06-30**) |

---

## 5. Recommended Stage 8 Model Matrix

| Domain | Recommended Primary Model | Secondary / Baseline Model | Target Evaluation Metric |
|---|---|---|---|
| **Customer Churn** | XGBoost (`scale_pos_weight=21.73`) | Logistic Regression (ElasticNet) | AUC-ROC > 0.75, F1 @ threshold < 0.30 |
| **Demand Forecasting** | XGBoost Regressor (Lags + Calendar) | Prophet (Tier-1 SKUs) | MAPE < 50.0% (Beating 90.61% baseline) |
| **Inventory Stockout** | Logistic Regression / Decision Tree | Naïve Reorder Rule | AUC-ROC > 0.9900 |
| **Machine Telemetry** | Isolation Forest (Per-Type Z-Score) | DBSCAN Clustering | Contamination Rate Stability = 5.00% |

---

## 6. Official Stage Completion Statement

> **STAGE 7 IS OFFICIALLY COMPLETE AND FULLY VALIDATED.**  
> - 6/6 Notebooks executed end-to-end against PostgreSQL with outputs embedded.  
> - 23/23 Control-total checks passed with $0.00 financial drift.  
> - 58 Statistical hypothesis tests executed and documented.  
> - `scripts/run_stage7_notebooks.py` executed cleanly with exit code 0.  
> - `docs/data_science/stage7_execution_report.json` generated (`"overall_status": "PASS"`).  
>  
> 🛑 **STAGE 8 HAS NOT BEEN STARTED.** The project is paused awaiting explicit user authorization to proceed to ML Model Training.
