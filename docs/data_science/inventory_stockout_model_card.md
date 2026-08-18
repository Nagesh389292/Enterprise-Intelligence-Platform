# Production Model Card — Stage 8C.1: Inventory Stockout Risk & 7-Day Forecasting

## Model Architecture Overview
- **Model A (Operational State Monitoring):** Identifies items currently below reorder threshold (`current_stockout_risk_flag`).
- **Model B (True 7-Day Predictive Forecast):** Forecasts whether an SKU at timestamp $T$ will fall below reorder point between $T+1$ and $T+7$ (`will_stockout_next_7d`).
- **Champion Architecture:** `XGBoost_Stockout_Classifier` (Model B)
- **Version:** 1.1.0
- **Dataset Grain:** 1 row per inventory item snapshot ($n=400$ items)
- **Model B Class Prevalence:** 21.25% positive 7-day stockout cases (85 / 400)
- **Leakage Audit Status:** 🟢 **PASSED** (Direct target formula variables `quantity_available`, `reorder_point`, `days_of_supply` strictly excluded)

---

## 5-Fold Stratified Cross-Validation Scorecard (Model B: True 7-Day Forecast)

| Model Architecture | ROC-AUC | PR-AUC | Precision | Recall | F1-Score | Brier Score | Verdict |
|---|---|---|---|---|---|---|---|
| **Reorder Point Rule Baseline** | 0.3637 | 0.2061 | 0.0481 | 0.1176 | 0.0683 | 0.2139 | Heuristic Rule |
| **Inventory Threshold Rule Baseline** | 0.2399 | 0.1365 | 0.0800 | 0.1882 | 0.1123 | 0.2791 | Heuristic Rule |
| **Logistic Regression Classifier** | 0.9547 | 0.8798 | 0.7170 | 0.8941 | 0.7958 | 0.0813 | Linear Balanced |
| **Random Forest Classifier** | 0.9419 | 0.8178 | 0.6514 | 0.8353 | 0.7320 | 0.1108 | Tree Bagging |
| **XGBoost Stockout Classifier** | 0.9802 | 0.9425 | 0.8043 | 0.8706 | 0.8362 | 0.0491 | 🏆 **Champion** |
| **LightGBM Stockout Classifier** | 0.9762 | 0.9274 | 0.7849 | 0.8588 | 0.8202 | 0.0566 | Leaf-wise Tree |

---

## Leakage Remediation & Feature Governance

- **Rejected Leaked Features:** `quantity_available` (formula variable), `reorder_point` (formula variable), `days_of_supply` (univariate AUC = 1.0000), `quantity_on_hand` (formula variable), `quantity_allocated` (formula variable), `is_below_reorder_point` (exact proxy).
- **Allowed Leak-Free Features:** `reorder_quantity`, `unit_cost`, `unit_price`, `inventory_value_usd`, `category_name`, `warehouse_location`.

---

## Simulated Operational Financial Impact Note

- **Cost Assumptions (Simulated Scenario):** Stockout Event = $100 per unmitigated stockout; Proactive Replenishment = $10 per action.
- **Operational Savings:** Under the simulated cost parameters, the model reduces estimated stockout-related operational expenses by **78.47%**.
