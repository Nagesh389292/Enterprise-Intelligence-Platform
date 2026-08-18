"""
scripts/train_machine_anomaly_model.py
---------------------------------------
Training & Evaluation Script for Problem A — Unsupervised Machine Telemetry Anomaly Detection:
- Evaluates Z-Score, IQR, and Isolation Forest anomaly detectors
- Computes detection rate, alerts/machine/day, precision, recall, F1, and score stability
- Generates production model card docs/data_science/machine_anomaly_model_card.md
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_science.models.machine_anomaly_trainer import MachineAnomalyPipeline
from data_science.config import PALETTE, FIGURE_DPI


def run_machine_anomaly_training():
    print("=" * 80)
    print("STAGE 8D — PROBLEM A: UNSUPERVISED REAL-TIME ANOMALY DETECTION")
    print("=" * 80)

    pipeline = MachineAnomalyPipeline(contamination=0.03, random_state=42)

    # 1. Load Telemetry Data
    df = pipeline.load_data()
    print(f"Loaded Telemetry Dataset: {len(df):,} records across {df['machine_id'].nunique()} machines.\n")

    # 2. Evaluate All Anomaly Methods
    results, (z_preds, iqr_preds, iso_preds, iso_scores) = pipeline.evaluate_all_anomaly_methods(df)

    print("--- PROBLEM A: UNSUPERVISED ANOMALY DETECTION SCORECARD ---")
    print(f"{'Method Name':<30} | {'Detections':<10} | {'Det Rate':<9} | {'Alerts/Mach/Day':<16} | {'Precision':<9} | {'Recall':<8} | {'F1-Score':<8}")
    print("-" * 105)
    for mname, res in results.items():
        print(f"{mname:<30} | {res['detected_anomalies']:<10} | {res['detection_rate']:<9.2%} | {res['alerts_per_machine_day']:<16.2f} | {res['precision']:<9.4f} | {res['recall']:<8.4f} | {res['f1']:<8.4f}")

    # 3. Fit & Save Champion Isolation Forest Model
    os.makedirs("models/telemetry", exist_ok=True)
    _, _, iso_model = pipeline.train_isolation_forest(df)
    model_path = "models/telemetry/isolation_forest_anomaly_model.pkl"
    joblib.dump(iso_model, model_path)

    metadata = {
        "model_name": "Isolation_Forest_Detector",
        "contamination": 0.03,
        "n_samples": len(df),
        "n_machines": int(df["machine_id"].nunique()),
        "sensor_cols": pipeline.sensor_cols,
        "detected_anomalies": results["Isolation_Forest_Detector"]["detected_anomalies"],
        "detection_rate": results["Isolation_Forest_Detector"]["detection_rate"],
        "alerts_per_machine_day": results["Isolation_Forest_Detector"]["alerts_per_machine_day"],
        "precision": results["Isolation_Forest_Detector"]["precision"],
        "recall": results["Isolation_Forest_Detector"]["recall"],
        "f1": results["Isolation_Forest_Detector"]["f1"]
    }

    with open("models/telemetry/isolation_forest_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved Isolation Forest model to {model_path}")
    print("Saved metadata to models/telemetry/isolation_forest_metadata.json")

    # 4. Generate Production Model Card
    card_content = f"""# Production Model Card — Stage 8D Problem A: Real-Time Anomaly Detection

## Model Architecture Overview
- **Question Addressed:** "Is this machine behaving abnormally at time T?"
- **Model Type:** Unsupervised `IsolationForest(contamination=0.03, n_estimators=150)`
- **Dataset Size:** {len(df):,} telemetry minute records across {df['machine_id'].nunique()} machines
- **Multi-Sensor Inputs:** `avg_temperature_c`, `avg_vibration_rms`, `avg_pressure_psi`, `avg_power_kw`

---

## Unsupervised Anomaly Scorecard

| Method Name | Detections | Detection Rate | Alerts / Machine / Day | Precision | Recall | F1-Score | Status |
|---|---|---|---|---|---|---|---|
| **Statistical Z-Score Baseline** | {results['Statistical_ZScore_Baseline']['detected_anomalies']} | {results['Statistical_ZScore_Baseline']['detection_rate']:.2%} | {results['Statistical_ZScore_Baseline']['alerts_per_machine_day']:.2f} | {results['Statistical_ZScore_Baseline']['precision']:.4f} | {results['Statistical_ZScore_Baseline']['recall']:.4f} | {results['Statistical_ZScore_Baseline']['f1']:.4f} | Z > 3.0 Rule |
| **Robust IQR Baseline** | {results['Robust_IQR_Baseline']['detected_anomalies']} | {results['Robust_IQR_Baseline']['detection_rate']:.2%} | {results['Robust_IQR_Baseline']['alerts_per_machine_day']:.2f} | {results['Robust_IQR_Baseline']['precision']:.4f} | {results['Robust_IQR_Baseline']['recall']:.4f} | {results['Robust_IQR_Baseline']['f1']:.4f} | 1.5 * IQR Rule |
| **Isolation Forest Detector** | {results['Isolation_Forest_Detector']['detected_anomalies']} | {results['Isolation_Forest_Detector']['detection_rate']:.2%} | {results['Isolation_Forest_Detector']['alerts_per_machine_day']:.2f} | {results['Isolation_Forest_Detector']['precision']:.4f} | {results['Isolation_Forest_Detector']['recall']:.4f} | {results['Isolation_Forest_Detector']['f1']:.4f} | 🏆 **Champion** |

---

## Operational Guidance & Limitations
- **No Accuracy Metric:** Accuracy is non-informative for rare unsupervised anomaly detection; alert rate, score stability, and recall are used.
- **Continuous Anomaly Score:** Normalized to $[0, 1]$ for real-time alerting dashboards.
"""

    os.makedirs("docs/data_science", exist_ok=True)
    with open("docs/data_science/machine_anomaly_model_card.md", "w", encoding="utf-8") as f:
        f.write(card_content)

    print("Generated production model card: docs/data_science/machine_anomaly_model_card.md")
    print("=" * 80)


if __name__ == "__main__":
    run_machine_anomaly_training()
