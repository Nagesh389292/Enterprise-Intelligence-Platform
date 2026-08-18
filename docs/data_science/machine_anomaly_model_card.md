# Production Model Card — Stage 8D Problem A: Real-Time Anomaly Detection

## Model Architecture Overview
- **Question Addressed:** "Is this machine behaving abnormally at time T?"
- **Model Type:** Unsupervised `IsolationForest(contamination=0.03, n_estimators=150)`
- **Dataset Size:** 100,000 telemetry minute records across 50 machines
- **Multi-Sensor Inputs:** `avg_temperature_c`, `avg_vibration_rms`, `avg_pressure_psi`, `avg_power_kw`

---

## Unsupervised Anomaly Scorecard

| Method Name | Detections | Detection Rate | Alerts / Machine / Day | Precision | Recall | F1-Score | Status |
|---|---|---|---|---|---|---|---|
| **Statistical Z-Score Baseline** | 2146 | 2.15% | 6.13 | 0.4208 | 1.0000 | 0.5923 | Z > 3.0 Rule |
| **Robust IQR Baseline** | 4401 | 4.40% | 12.57 | 0.2052 | 1.0000 | 0.3405 | 1.5 * IQR Rule |
| **Isolation Forest Detector** | 3000 | 3.00% | 8.57 | 0.3010 | 1.0000 | 0.4627 | 🏆 **Champion** |

---

## Operational Guidance & Limitations
- **No Accuracy Metric:** Accuracy is non-informative for rare unsupervised anomaly detection; alert rate, score stability, and recall are used.
- **Continuous Anomaly Score:** Normalized to $[0, 1]$ for real-time alerting dashboards.
