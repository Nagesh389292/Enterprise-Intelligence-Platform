# Model Selection Brief — NexaCore Enterprise Intelligence Platform
# Stage 7: Technical Justification for Stage 8 ML Models

**Last Updated:** 2026-08-18  
**Basis:** Executed Stage 7 Notebook Analysis (`docs/data_science/stage7_execution_report.json`)  
**Status:** Analytical Decision Framework Approved for Stage 8 Handoff  

---

## Technical Decision Summary

```
Observed Data Characteristics
        ↓
Statistical Findings & Baseline Benchmark
        ↓
Candidate Models Evaluation
        ↓
Recommended Stage 8 Models
        ↓
Validation Strategy & Threshold Tuning
```

---

## 1. Customer Churn Classification

### Observed Data Characteristics
- **Dataset Size:** 1,000 customers (`analytics.ml_customer_churn_features`).
- **Class Imbalance:** 4.40% churn rate (44 churned vs 956 retained) → **21.73 : 1 imbalance ratio**.
- **Univariate Predictors:** Individual linear features (`total_spend_to_cutoff` p=0.1457, `recency_days_at_cutoff` p=0.6362, `account_tenure_days` p=0.1542, `avg_csat_score` p=0.2036) fail to yield statistically significant linear separation univariately.

### Baseline Benchmark
- **Majority Class Naïve Baseline:** AUC = 0.5000 (predict all retained).
- **Linear Logistic Regression (3-fold Stratified CV):** **AUC = 0.4396 ± 0.0278** (Train AUC = 0.7013).
  - *Data Science Insight:* Linear Logistic Regression heavily overfits the 44 positive instances and performs worse than random guessing (0.4396 vs 0.5000) due to boundary non-linearity and unweighted class imbalance.

### Candidate Models Evaluated for Stage 8
1. **XGBoost Classifier (Primary Recommendation):**
   - *Why:* Non-linear decision trees capture complex multi-feature interactions; `scale_pos_weight = 21.73` handles class imbalance natively; regularisation (`max_depth=3-5`, `subsample=0.8`) prevents overfitting on 44 positives.
   - *Explainability:* SHAP (SHapley Additive exPlanations) values provide local and global feature attribution for business stakeholders.
2. **Random Forest Classifier (Backup Benchmark):**
   - *Why:* Ensemble of bagging trees resists variance; handles non-linear boundaries.
3. **Logistic Regression with ElasticNet & Class Weights (Linear Baseline):**
   - *Why:* Benchmark to demonstrate the necessity of non-linear tree boosting.

### Validation Strategy & Metrics
- **Cross-Validation:** 5-fold Stratified K-Fold.
- **Primary Metric:** **AUC-ROC** (discrimination across all thresholds).
- **Secondary Metrics:** **PR-AUC (Precision-Recall AUC)** & **F1-Score @ optimal threshold**.
- **Business Cost Threshold Optimization:** In churn prevention, a False Negative (losing a $77k LTV customer) is 10x more costly than a False Positive (sending a retention voucher to a retained customer). Stage 8 will optimize the decision threshold **< 0.30** to maximize Recall.

---

## 2. Demand Forecasting

### Observed Data Characteristics
- **Dataset Grain:** 18,100 daily SKU records (100 products × 181 days, Jan 1 to Jun 30, 2026).
- **Predictor Validations:**
  - `lag_7_units_sold`: **r = 0.4752** (p = 0.000000 ***)
  - `lag_14_units_sold`: **r = 0.4625** (p = 0.000000 ***)
  - `rolling_7_day_avg_units`: **r = 0.6473** (p = 0.000000 ***)

### Baseline Benchmarks
- **Naïve Lag-7 Persistence Model:** **MAE = 8.60**, **RMSE = 12.45**, **MAPE = 116.49%**.
- **Rolling 7-Day Average Baseline Model:** **MAE = 6.77**, **RMSE = 9.39**, **MAPE = 90.61%**.
  - *Data Science Insight:* Rolling 7-day smoothing beats Naïve Lag-7 by 25.88% MAPE points, proving that trend smoothing reduces point-wise daily noise.

### Candidate Models Evaluated for Stage 8
1. **XGBoost Regressor with Lag & Calendar Features (Primary Recommendation):**
   - *Why:* Incorporates `lag_7`, `lag_14`, `rolling_7d`, `day_of_week`, `month`, and `is_weekend` into a unified global model across all 100 SKUs. Capable of learning product-tier specific non-linearities.
2. **Prophet / SARIMA (Tier-1 High Forecastability SKUs):**
   - *Why:* For the 14 SKUs in the **HIGH Forecastability Tier (CV < 0.50)**, statistical time series models (Prophet/SARIMA) provide interpretable trend/seasonality decomposition.

### Validation Strategy & Metrics
- **Validation Split:** Temporal Time-Series Split (Train: Jan-May 2026, Test: June 2026 - 30 days holdout). Zero lookahead leakage.
- **Primary Metric:** **MAPE (Mean Absolute Percentage Error)** — Target: **< 50.0%** (beating the 90.61% baseline).
- **Secondary Metrics:** **MAE** & **RMSE**.

---

## 3. Inventory Stockout Risk Classification

### Observed Data Characteristics
- **Dataset Grain:** 400 point-in-time inventory records (`analytics.ml_inventory_stockout_risk`).
- **Stockout Risk Rate:** 21.25% (85 items at risk / 315 adequate).
- **Predictor Separability:**
  - `buffer_ratio` (`quantity_available / reorder_point`): **p = 0.000000 *** **, effect size = **-0.88 (Large)** (Medians: 0.47 vs 3.96).
  - `safety_margin` (`quantity_available - reorder_point`): **p = 0.000000 *** **, effect size = **-0.88 (Large)** (Medians: -181.0 vs 358.0 units).

### Baseline Benchmark
- **Logistic Regression (5-fold CV):** **AUC = 0.9993 ± 0.0014**.
  - *Data Science Insight:* Derived features `buffer_ratio` and `safety_margin` provide near-perfect linear separation.

### Candidate Models Evaluated for Stage 8
1. **Logistic Regression (Primary Recommendation):**
   - *Why:* Highly interpretable, lightweight, mathematically robust, achieves 0.999+ AUC without risk of overfitting on n=400.
2. **Decision Tree Classifier (Depth = 3) (Interpretable Rules Benchmark):**
   - *Why:* Generates explicit, human-readable operational decision rules for warehouse managers (e.g., `IF buffer_ratio <= 1.0 THEN FLAG_STOCKOUT`).
3. **XGBoost:** *NOT recommended* — high risk of overfitting on a 400-row cross-sectional snapshot with linearly separable derived features.

### Validation Strategy & Metrics
- **Cross-Validation:** 5-fold Stratified CV.
- **Metrics:** **AUC-ROC**, **Precision**, **Recall**, and **F1-Score**.

---

## 4. Machine Telemetry Anomaly Detection

### Observed Data Characteristics
- **Dataset Grain:** 100,000 minute-level telemetry rollups across 50 machines (`analytics.ml_machine_telemetry_features`).
- **Signal Properties:**
  - `avg_temperature_c`: Skewed, non-normal (D'Agostino p=0.000000), Kruskal-Wallis across machine types **H = 142.04, p = 0.000000 *** **.
  - `avg_vibration_rms`: Skewed, non-normal (D'Agostino p=0.000000), Kruskal-Wallis across machine types **H = 103.33, p = 0.000000 *** **.
  - Co-elevation correlation: **r = 0.6694 (p = 0.000000 ***)** between temperature and vibration.

### Baseline Benchmark
- **Univariate IQR Outlier Detection:** Identifies 3,240 temperature outliers (3.24%). Misses multi-signal co-elevations.

### Candidate Models Evaluated for Stage 8
1. **Isolation Forest with Per-Machine-Type Z-Score Normalization (Primary Recommendation):**
   - *Why:* Telemetry signal baselines differ significantly by `machine_type_name` (Kruskal-Wallis p < 0.001). Stage 8 must first normalize signals per machine type (`z_temp`, `z_vib`), then apply Isolation Forest at 5% contamination to isolate multi-dimensional anomalies.
2. **DBSCAN (Density-Based Spatial Clustering):**
   - *Why:* Identifies dense clusters of normal operation vs sparse noise points (anomalies).
3. **Supervised Classification:** *NOT feasible* — `fact_maintenance_events` contains only 3 records. Supervised learning is mathematically impossible without label synthesis.

### Validation Strategy & Metrics
- **Metrics:** Anomaly Rate Stability (5.00%), Signal Co-elevation Agreement (% anomalies with elevated temp AND vibration), and Precision/Recall against severe anomaly severity scores (> 0.70).

---

## Summary Matrix for Stage 8 Handoff

| Domain | Recommended Primary Model | Baseline Metric to Beat | Justification grounded in Stage 7 EDA |
|---|---|---|---|
| **Customer Churn** | XGBoost (`scale_pos_weight=21.73`) | Logistic Reg AUC = 0.4396 | Severe imbalance (4.4%), non-linear boundary; linear model fails |
| **Demand Forecasting** | XGBoost (Lags + Calendar) | Rolling 7d MAPE = 90.61% | Lags (r=0.48-0.65) highly significant; rolling 7d reduces noise |
| **Inventory Stockout** | Logistic Regression | LR 5-fold CV AUC = 0.9993 | Derived buffer_ratio provides near-linear separation (d=-0.88) |
| **Machine Telemetry** | Isolation Forest (Per-Type Z-Score) | Univariate IQR Outlier Rate | Signals non-normal, machine-type dependent; only 3 failure labels |
