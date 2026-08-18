# Feature Engineering Rationale — NexaCore Enterprise Intelligence Platform
# Stage 7: Feature Profiling, Selection & Transformation Plan

**Last Updated:** 2026-08-18  
**Basis:** Executed Stage 7 Feature Profiling & Hypothesis Testing (`docs/data_science/stage7_execution_report.json`)  
**Status:** Feature Engineering Specifications Approved for Stage 8 Pipeline  

---

## Executive Summary

This document specifies the exact feature candidate selection, transformation rules, anti-leakage constraints, and preprocessing pipelines required for Stage 8 model training. All specifications are grounded in Stage 7 empirical profiles and statistical tests.

---

## 1. Customer Churn Feature Set (`analytics.ml_customer_churn_features`)

### Feature Candidates & Selection Rationale

| Feature Name | Type | Scaling / Transformation | Selection Status | Empirical Stage 7 Rationale |
|---|---|---|---|---|
| `recency_days_at_cutoff` | Numeric | Log1p transform + RobustScaler | ✅ Selected | Core RFM recency metric |
| `total_orders_to_cutoff` | Numeric | RobustScaler | ✅ Selected | Volume metric; non-linear interaction with tenure |
| `total_spend_to_cutoff` | Numeric | Log1p transform + Standardized | ✅ Selected | High skewness; monetary scale |
| `avg_order_value_to_cutoff` | Numeric | RobustScaler | ✅ Selected | Spend per transaction |
| `avg_csat_score_to_cutoff` | Numeric | Standardized (Impute Median) | ✅ Selected | Customer satisfaction proxy |
| `total_support_tickets_to_cutoff` | Numeric | RobustScaler | ✅ Selected | Operational friction metric |
| `account_tenure_days` | Numeric | Standardized | ✅ Selected | Customer age metric |
| `order_frequency_30d` | Derived | Ratio (`total_orders / tenure * 30`) | ✅ Selected | Short-term velocity metric |
| `order_frequency_90d` | Derived | Ratio (`total_orders / tenure * 90`) | ✅ Selected | Medium-term velocity metric |
| `segment_name` | Categorical | One-Hot Encoding | ✅ Selected | Segment baseline differences |

### Anti-Leakage & Temporal Boundary Rules
- **Cutoff Date:** **2026-05-01** (Verified by Stage 4B Anti-Leakage Audit).
- **Feature Window:** All aggregates computed strictly on events $\le$ **2026-05-01**.
- **Target Window:** `is_churned_target` defined strictly on purchasing activity between **2026-05-02** and **2026-07-31**. Zero temporal overlap.

---

## 2. Demand Forecasting Feature Set (`analytics.ml_demand_forecasting_daily`)

### Feature Candidates & Selection Rationale

| Feature Name | Type | Transformation | Correlation with Target | Selection Status |
|---|---|---|---|---|
| `lag_7_units_sold` | Numeric Lag | Past 7-day value | **r = 0.4752** (p < 0.001) | ✅ Selected (Primary Lag) |
| `lag_14_units_sold` | Numeric Lag | Past 14-day value | **r = 0.4625** (p < 0.001) | ✅ Selected (Secondary Lag) |
| `rolling_7_day_avg_units` | Numeric Rolling | 7-day moving average | **r = 0.6473** (p < 0.001) | ✅ Selected (Strongest Predictor) |
| `rolling_30_day_avg_units` | Numeric Rolling | 30-day moving average | r = 0.5810 (p < 0.001) | ✅ Selected |
| `day_of_week` | Categorical | Cyclic Cosine/Sine encoding | Cyclical pattern | ✅ Selected |
| `month` | Categorical | One-Hot Encoding | Monthly seasonality | ✅ Selected |
| `is_weekend` | Binary | Direct Binary (0/1) | Weekend demand shift | ✅ Selected |
| `product_id` | Categorical | Entity Embedding / Target Enc | SKU identity | ✅ Selected |

### Anti-Leakage & Windowing Rules
- **Temporal Alignment:** For day $t$, features use only data from day $t-7$ or earlier for 7-day forecasts. Zero future information leakage.

---

## 3. Inventory Stockout Risk Feature Set (`analytics.ml_inventory_stockout_risk`)

### Feature Candidates & Selection Rationale

| Feature Name | Type | Transformation | Mann-Whitney p-value | Effect Size | Selection Status |
|---|---|---|---|---|---|
| `buffer_ratio` | Derived Ratio | `quantity_available / reorder_point` | **p = 0.000000 *** ** | **-0.88 (Large)** | ✅ Primary Predictor |
| `safety_margin` | Derived Difference | `quantity_available - reorder_point` | **p = 0.000000 *** ** | **-0.88 (Large)** | ✅ Primary Predictor |
| `quantity_available` | Numeric | RobustScaler | **p = 0.000000 *** ** | **0.51 (Medium)** | ✅ Selected |
| `quantity_on_hand` | Numeric | RobustScaler | **p = 0.000000 *** ** | **0.48 (Medium)** | ✅ Selected |
| `reorder_point` | Numeric | Standardized | **p = 0.000000 *** ** | **-0.52 (Medium)** | ✅ Selected |
| `days_of_supply` | Numeric | Log1p transform | p < 0.001 | 0.65 | ✅ Selected |
| `quantity_allocated` | Numeric | Exclude / Low Sig | p = 0.2041 (ns) | 0.06 | ❌ Dropped (Not Significant) |

---

## 4. Machine Telemetry Anomaly Feature Set (`analytics.ml_machine_telemetry_features`)

### Feature Candidates & Selection Rationale

| Feature Name | Preprocessing Rule | Kruskal-Wallis p-value | Selection Status | Rationale |
|---|---|---|---|---|
| `z_temperature` | Machine-Type Z-Score | **H = 142.04, p < 0.001** | ✅ Selected | Normalizes baseline temp differences across machine types |
| `z_vibration` | Machine-Type Z-Score | **H = 103.33, p < 0.001** | ✅ Selected | Normalizes baseline vibration differences across machine types |
| `avg_pressure_psi` | Global Standardized | H = 1.76, p = 0.7789 (ns) | ✅ Selected | Pressure is uniform across machine types |
| `avg_power_kw` | Global Standardized | H = 2.57, p = 0.6321 (ns) | ✅ Selected | Power is uniform across machine types |
| `rolling_10min_avg_temp` | Rolling 10m Mean | Smoothed Trend | ✅ Selected | Noise reduction for thermal inertia |
| `temp_spread` | `max_temp - avg_temp` | Spiking Metric | ✅ Selected | Temperature sudden spike indicator |

---

## Preprocessing Pipeline Architecture (Scikit-Learn ColumnTransformer)

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

churn_numeric_cols = [
    "total_orders", "total_revenue", "avg_order_value",
    "days_since_last_order", "order_frequency_30d", "order_frequency_90d",
    "avg_csat_score", "total_support_tickets", "days_as_customer"
]

churn_preprocessor = ColumnTransformer(
    transformers=[
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]), churn_numeric_cols),
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), ["customer_segment"]),
    ]
)
```
