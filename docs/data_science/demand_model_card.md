# Production Model Card — Stage 8B: SKU Demand Forecasting

## Model Overview
- **Model Name:** Champion SKU Demand Forecast Regressor (`Ridge_Linear_Regressor`)
- **Version:** 1.0.0
- **Model Type:** Gradient Tree Boosting Regressor
- **Task:** Time-Series Regression (Target: `units_sold_target` ∈ $\mathbb{Z}_{\ge 0}$)
- **Dataset Grain:** Daily product SKU level ($n=18,100$ records across 100 products, 181 days)
- **Validation Methodology:** 5-Fold Expanding Window Time-Series Cross Validation (`sklearn.model_selection.TimeSeriesSplit`)

---

## Cross-Validation Performance Scorecard (5-Fold TimeSeriesSplit)

## Cross-Validation Performance Scorecard (5-Fold TimeSeriesSplit)

| Model Architecture | RMSE (units) | MAE (units) | $R^2$ Score | MAPE (%) | Benchmarking Verdict |
|---|---|---|---|---|---|
| **Naïve Lag-7 Baseline** | 12.15 | 8.45 | 0.0011 | 215.56% | Persistence Baseline |
| **Rolling 7-Day Mean Baseline** | 9.20 | 6.66 | 0.4282 | 195.29% | Stage 7 EDA Benchmark |
| **Ridge Linear Regressor** | **8.81** | **6.48** | **0.4736** | **204.01%** | 🏆 **Champion Regressor** |
| **XGBoost Demand Regressor** | 8.90 | 6.54 | 0.4627 | 204.63% | Gradient Tree Boosting |
| **LightGBM Demand Regressor** | 8.91 | 6.53 | 0.4623 | 204.07% | Leaf-wise Tree Boosting |

---

## Baseline Beat & Improvement Summary

- **Naïve Lag-7 RMSE:** 12.15 units ($R^2 = 0.0011$)
- **Rolling 7-Day Mean RMSE:** 9.20 units ($R^2 = 0.4282$)
- **Champion Ridge Linear Regressor RMSE:** **8.81 units** ($R^2 = 0.4750$)
- **Net Improvement:** Beats Naïve Lag-7 by **3.35 units RMSE** ($+0.4739$ $R^2$ boost) and Rolling 7-Day Average by **0.39 units RMSE** ($+0.0468$ $R^2$ boost).

---

## Metric Governance Note on MAPE vs WAPE

- **Zero Demand Inflation:** 30.03% of dataset days have zero demand ($y=0$). On zero-demand days, relative percentage error is undefined/inflated (average MAPE = 479.95%), inflating dataset-wide MAPE to ~204%.
- **Primary Supply Chain Metric:** **WAPE (Weighted Absolute Percentage Error = 61.08%)** and **RMSE (8.81 units)** are established as primary evaluation metrics for production deployment.

---

## Top SHAP Feature Drivers

1. `rolling_avg_7d` (7-day moving average captures baseline demand level)
2. `units_sold_lag1` (Immediate previous day demand captures short-term autocorrelation)
3. `units_sold_lag7` (Weekly seasonality lag)
4. `rolling_7_std` (Demand volatility / variance)
5. `day_of_week_num` (Weekly consumer purchasing pattern)

---

## Model Governance & Operational Guardrails

1. **Strict Non-Random Validation Rule:**  
   Random train/test splitting is strictly prohibited for demand forecasting due to temporal data leakage. All evaluations use expanding-window `TimeSeriesSplit`.
2. **Non-Negative Output Post-Processing:**  
   Predictions are post-processed with `np.maximum(y_pred, 0.0)` to enforce physical inventory supply chain constraints.
3. **Re-training Schedule:**  
   Retrain monthly upon batch ingestion of `analytics.ml_demand_forecasting_daily`.
