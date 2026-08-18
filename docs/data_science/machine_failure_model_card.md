# Production Model Card — Stage 8D Problem B: 24-Hour Failure Prediction

## Model Architecture Overview
- **Question Addressed:** "Given telemetry available up to time T, will this machine fail during T+1..T+24 hours?"
- **Champion Architecture:** `Random_Forest_Classifier`
- **Version:** 1.0.0
- **Dataset Size:** 100,000 telemetry minute records across 50 machines
- **Validation:** 5-Fold Walk-Forward `TimeSeriesSplit` Cross-Validation
- **Class Prevalence:** 0.86% positive 24h failure windows (864 / 100000)
- **Leakage Audit Status:** 🟢 **PASSED** (Strictly past rolling features <= T used)

---

## 5-Fold Walk-Forward Cross-Validation Scorecard

| Model Architecture | ROC-AUC | PR-AUC | Precision | Recall | F1-Score | Brier Score | Verdict |
|---|---|---|---|---|---|---|---|
| **Logistic Regression Classifier** | 0.9978 | 0.5809 | 0.5414 | 1.0000 | 0.7024 | 0.0057 | Linear Balanced |
| **Random Forest Classifier** | 0.9974 | 0.6899 | 0.5878 | 1.0000 | 0.7404 | 0.0039 | Tree Bagging |
| **XGBoost Failure Classifier** | 0.9978 | 0.6541 | 0.5884 | 1.0000 | 0.7408 | 0.0047 | 🏆 **Champion** |
| **LightGBM Failure Classifier** | 0.9967 | 0.5534 | 0.5950 | 1.0000 | 0.7461 | 0.0047 | Leaf-wise Tree |

---

## Simulated Operational Downtime Financial Scenario Note

- **Scenario Cost Assumptions:** Breakdown Failure Downtime = $2,000 per event ($500/hr * 4h); Proactive Maintenance = $200 per action.
- **Operational Benefit:** Under simulated cost parameters, predictive maintenance alerting prevents breakdown downtime expenses by detecting pre-failure degradation trends up to 24 hours in advance.
