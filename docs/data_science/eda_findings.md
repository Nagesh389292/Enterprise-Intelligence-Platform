# EDA Findings — NexaCore Enterprise Intelligence Platform
# Stage 7: Empirical Data Exploration & Statistical Analysis

**Last Updated:** 2026-08-18  
**Analysis Status:** 🟢 6/6 Notebooks Executed End-to-End (`docs/data_science/stage7_execution_report.json`)  
**Source Database:** PostgreSQL `nexacore_dw` (Analytics Schema)  

---

## Executive Summary

Stage 7 conducted structured, empirical exploratory data analysis across five business domains:
customer churn, demand forecasting, inventory stockout risk, machine anomaly detection,
and cross-domain statistical testing. All findings are grounded in verified cell execution
and actual statistical tests against the live dataset.

---

## 1. Revenue & Business Health (Notebook 01)

| Metric | Computed Value | Canonical Control Target | Status |
|---|---|---|---|
| Net Revenue | $77,237,960.93 | $77,237,960.93 | ✅ Exact Match ($0.00 drift) |
| Total Orders | 10,000 | 10,000 | ✅ Exact Match |
| Order Items | 35,193 | 35,193 | ✅ Exact Match |
| Customers | 1,000 | 1,000 | ✅ Exact Match |
| Avg CSAT Score | 3.38 | 3.38 | ✅ Exact Match |
| Inventory On Hand | 210,174 units | 210,174 units | ✅ Exact Match |
| Low Stock Items | 85 items | 85 items | ✅ Exact Match |
| Machine Fleet | 50 machines | 50 machines | ✅ Exact Match |
| Telemetry Records | 100,000 records | 100,000 records | ✅ Exact Match |

**Key Empirical Findings:**
- **Revenue Concentration:** Lorenz curve analysis yields a Gini coefficient of **0.2060**, indicating a relatively balanced revenue distribution across the 1,000 customers.
- **Discount Rate:** Average discount rate across order items is **7.51%** ($6,275,977.59 total discounts on $83,513,938.52 gross revenue).
- **Fleet Anomaly Baseline:** Temperature and vibration severe anomaly flags occur at **0.90%** of total minute rollups (900 out of 100,000 records).

---

## 2. Customer Churn Analysis (Notebook 02)

**Business Problem:** Predict which of the 1,000 customers will churn (stop purchasing) in the next 90 days.

| Metric / Test | Empirical Result | Statistical Interpretation |
|---|---|---|
| **Dataset Size** | 1,000 customers | `analytics.ml_customer_churn_features` |
| **Churn Rate** | **4.40%** (44 churned, 956 retained) | Severe class imbalance (**21.73 : 1** ratio) |
| **Recency (`recency_days_at_cutoff`)** | Mann-Whitney U, p = 0.6362 (ns) | Univariate distribution overlap; linear separation absent |
| **Total Spend (`total_spend_to_cutoff`)** | Mann-Whitney U, p = 0.1457 (ns) | Spend alone does not predict churn univariately |
| **Account Tenure (`account_tenure_days`)** | Mann-Whitney U, p = 0.1542 (ns) | Tenure shows weak univariate effect |
| **Support Tickets (`total_support_tickets_to_cutoff`)** | Mann-Whitney U, p = 0.9090 (ns) | Ticket volume alone does not differentiate churners |
| **CSAT (`avg_csat_score_to_cutoff`)** | Mann-Whitney U, p = 0.2036 (ns) | Average CSAT score shows non-significant univariate difference |
| **Segment Association** | Chi-square test, p = 0.8241 (ns) | Segment churn rates: Enterprise 4.2%, Mid-Market 3.8%, SMB 4.7% |
| **Baseline Logistic Regression (3-fold CV)** | **AUC = 0.4396 ± 0.0278** (Train AUC = 0.7013) | Standard linear Logistic Regression fails heavily (worse than 0.50 AUC random guess) due to extreme 4.4% imbalance and non-linear boundaries |

**Crucial Data Science Finding for Stage 8:**
Linear models with standard loss functions perform terribly on this dataset (0.4396 AUC).
Stage 8 **must** utilize non-linear tree-based models (XGBoost / LightGBM) combined with `scale_pos_weight` imbalance handling and threshold optimization (< 0.30) to achieve positive predictive value.

---

## 3. Demand Forecasting (Notebook 03)

**Business Problem:** Forecast daily units sold per product across 100 SKUs over 181 days (Jan 1, 2026 to Jun 30, 2026).

| Predictor / Baseline Model | Empirical Result | Statistical Significance |
|---|---|---|
| **Dataset Grain** | 18,100 daily SKU records | 181 days × 100 products |
| **Lag-7 Predictor (`lag_7_units_sold`)** | Pearson **r = 0.4752** | p = 0.000000 *** (Statistically Significant) |
| **Lag-14 Predictor (`lag_14_units_sold`)** | Pearson **r = 0.4625** | p = 0.000000 *** (Statistically Significant) |
| **Rolling 7d Avg (`rolling_7_day_avg_units`)** | Pearson **r = 0.6473** | p = 0.000000 *** (Strongest Predictor) |
| **Naïve Persistence Baseline (Lag-7)** | **MAE = 8.60**, **RMSE = 12.45**, **MAPE = 116.49%** | Naïve persistence struggles on volatile SKUs |
| **Rolling 7-Day Average Baseline** | **MAE = 6.77**, **RMSE = 9.39**, **MAPE = 90.61%** | **25.88% MAPE improvement** over Naïve Lag-7 |

**Forecastability Tiers (CV = std/mean across 100 SKUs):**
- **HIGH Forecastability (CV < 0.50):** 14 SKUs — highly stable demand, prime targets for SARIMA/Prophet.
- **MEDIUM Forecastability (0.50 ≤ CV ≤ 1.00):** 62 SKUs — moderate volatility, well suited for XGBoost with lag features.
- **LOW Forecastability (CV > 1.00):** 24 SKUs — intermittent/high-variance demand, best modeled via aggregate rolling averages.

---

## 4. Inventory Stockout Risk (Notebook 04)

**Business Problem:** Predict stockout risk flag (`stockout_risk_flag_target`) across 400 inventory records.

| Feature / Model | Empirical Result | Test Statistic & Significance | Effect Size |
|---|---|---|---|
| **Stockout Risk Prevalence** | **21.25%** (85 at-risk items / 315 adequate) | Baseline prevalence | N/A |
| **Quantity Available (`quantity_available`)** | Medians: 155.0 vs 585.0 units | Mann-Whitney U, **p = 0.000000 *** ** | Medium (**0.51**) |
| **Quantity On Hand (`quantity_on_hand`)** | Medians: 208.0 vs 624.0 units | Mann-Whitney U, **p = 0.000000 *** ** | Medium (**0.48**) |
| **Reorder Point (`reorder_point`)** | Medians: 500.0 vs 100.0 units | Mann-Whitney U, **p = 0.000000 *** ** | Medium (**-0.52**) |
| **Buffer Ratio (`quantity_available / reorder_point`)** | Medians: **0.47 vs 3.96** | Mann-Whitney U, **p = 0.000000 *** ** | Large (**-0.88**) |
| **Safety Margin (`quantity_available - reorder_point`)** | Medians: **-181.0 vs 358.0 units** | Mann-Whitney U, **p = 0.000000 *** ** | Large (**-0.88**) |
| **Category Association** | Chi-square test, p = 0.7473 (ns) | Cramér's V = 0.076 | Non-significant |
| **Warehouse Association** | Chi-square test, p = 0.9138 (ns) | Cramér's V = 0.049 | Non-significant |
| **Baseline Logistic Regression (5-fold CV)** | **AUC = 0.9993 ± 0.0014** | Near-perfect separation via derived `buffer_ratio` & `safety_margin` |

**Critical Dataset Limitation:**
`analytics.ml_inventory_stockout_risk` is a **400-row point-in-time snapshot** (dated 2026-06-30). It is **not** a longitudinal time series. Simple interpretable models (Logistic Regression / Decision Tree) are optimal; XGBoost is unnecessary and prone to overfitting on this size.

---

## 5. Machine Telemetry Anomaly Detection (Notebook 05)

**Business Problem:** Detect anomalous operational patterns across 100,000 minute-level telemetry records for 50 machines.

| Signal / Model | Empirical Distribution | Normality & Group Differences | Anomaly Rate |
|---|---|---|---|
| **`avg_temperature_c`** | Non-normal (skewed) | D'Agostino p = 0.000000, Kruskal-Wallis **H = 142.04, p = 0.000000 *** ** | Baseline shifts across machine types |
| **`avg_vibration_rms`** | Non-normal (skewed) | D'Agostino p = 0.000000, Kruskal-Wallis **H = 103.33, p = 0.000000 *** ** | Baseline shifts across machine types |
| **`avg_pressure_psi`** | Normal | D'Agostino p = 0.5694 (normal), Kruskal-Wallis H = 1.76, p = 0.7789 (ns) | Uniform across types |
| **`avg_power_kw`** | Normal | D'Agostino p = 0.5943 (normal), Kruskal-Wallis H = 2.57, p = 0.6321 (ns) | Uniform across types |
| **Temp-Vibration Co-elevation** | Pearson **r = 0.6694** | p = 0.000000 *** (Strong multi-signal interaction) | Core failure mode indicator |
| **Isolation Forest (5% contamination)** | Multivariate (4 signals) | Detects **5,000 anomalous minutes** (5.00%) | Per-machine-type normalization required |

**Critical Dataset Limitation:**
Only **3 maintenance events** exist in `fact_maintenance_events`. Supervised classification is impossible. Unsupervised anomaly detection (Isolation Forest / DBSCAN) with per-machine-type Z-score normalization is the only valid technical approach.

---

## 6. Cross-Domain Statistical Framework (Notebook 06)

| Hypothesis Test | Test Used | Empirical Result | Business Significance |
|---|---|---|---|
| **H1: Segment vs AOV** | One-way ANOVA | F = 0.56, **p = 0.5715** (ns), η² = 0.001 | Order value is consistent across segments |
| **H2: Ticket Priority vs CSAT** | Kruskal-Wallis H | **H = 28.40, p = 0.000000 *** ** | Urgent/Critical tickets receive significantly lower CSAT |
| **H3: Warehouse vs Stockout Risk** | Kruskal-Wallis H | H = 0.52, **p = 0.9141** (ns) | Stockout risk is evenly spread across warehouses |
| **H4: Segment vs Channel ID** | Chi-square test | χ² = 2.65, **p = 0.8531** (ns), Cramér's V = 0.008 | Channel choice is independent of customer segment |
| **Multiple Testing Correction** | FDR (Benjamini-Hochberg) | **14 significant tests preserved** | Controls false discovery rate across exploratory tests |
| **A/B Test Sample Size** | Power Analysis (α=0.05, 80% power) | Requires **n = 3,420 per arm** to detect 2% churn reduction | Current n=1,000 sample can only detect >10% churn drops |

---

## Summary of All Executed Artifacts

- **Notebooks Executed:** 6 / 6 (`.ipynb` files updated with full cell outputs)
- **Execution Report:** `docs/data_science/stage7_execution_report.json` (Status: PASS)
- **Figures Saved:** 18 PNG charts in `docs/data_science/figures/`
- **Reproducibility Runner:** `scripts/run_stage7_notebooks.py` (Exit code: 0)
