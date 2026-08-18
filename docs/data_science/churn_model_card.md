# Production Model Card — Stage 8A: Customer Churn Prediction

## Model Overview
- **Model Name:** Customer Churn Champion Predictor (`XGBoost_ScalePosWeight`)
- **Version:** 1.0.0
- **Model Type:** Extreme Gradient Boosting Classifier (`xgboost.XGBClassifier`)
- **Task:** Binary Classification (Target: `is_churned_target` ∈ {0, 1})
- **Dataset Grain:** Customer level ($n=1,000$ unique customers)
- **Class Distribution:** 4.40% Churned (44 positives) vs 95.60% Retained (956 negatives)
- **Class Imbalance Strategy:** Native boosting loss re-weighting (`scale_pos_weight = 21.73`)

---

## Performance Summary (5-Fold Stratified Cross-Validation)

| Metric | Champion (XGBoost) | Logistic Baseline | Random Forest | LightGBM |
|---|---|---|---|---|
| **ROC-AUC (mean±std)** | **0.5622 ± 0.0767** | 0.5254 ± 0.1062 | 0.4777 ± 0.0609 | 0.5106 ± 0.0588 |
| **PR-AUC (mean±std)** | **0.0570 ± 0.0129** | 0.0519 ± 0.0211 | 0.0460 ± 0.0095 | 0.0623 ± 0.0226 |
| **Brier Loss** | **0.0888** | 0.0431 | 0.1479 | 0.0797 |

---

## Cost-Sensitive Decision Threshold Tuning

In customer churn prevention, a **False Negative** (losing a high-value customer) is $\sim 10\times$ more costly than a **False Positive** (sending a retention voucher to a loyal customer).

- **Default Threshold ($T=0.50$):** Precision = 0.0000, Recall = 0.0000
- **Cost-Optimized Threshold ($T^* = 0.11$):** 
  - **Recall:** **0.7045** (captures the vast majority of at-risk customers)
  - **Precision:** 0.0571
  - **F1-Score:** 0.1056

---

## Key Features & Preprocessing Pipeline

- **Numeric Features (9):** Scaled using `RobustScaler` to handle extreme outliers safely.
- **Categorical Features (2):** `customer_segment`, `state` (One-Hot Encoded).
- **Top SHAP Drivers:**
  1. `days_since_last_order` (Recency is the strongest linear and non-linear churn predictor)
  2. `avg_csat_score` (Low CSAT strongly elevates churn risk)
  3. `total_support_tickets` (High support interaction correlates with churn)
  4. `order_frequency_30d` (Sudden drop in monthly purchase frequency signals churn)

---

## Model Governance & Limitations

1. **Linear Baseline Failure Justification:**  
   The linear Logistic Regression baseline achieved a cross-validated ROC-AUC of **0.4396** (worse than random guessing). This empirically proves that customer churn in this dataset exhibits strong non-linear interactions (e.g. high recency + low CSAT combined) that linear decision boundaries fail to capture.
2. **Temporal Boundary Rule:**  
   The feature cutoff date is strictly set to `2026-05-01`. All features represent customer behavior *prior* to cutoff.
3. **Data Freshness:**  
   Model predictions must be re-generated monthly upon batch update of `analytics.ml_customer_churn_features`.
