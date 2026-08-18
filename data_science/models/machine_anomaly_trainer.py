"""
data_science/models/machine_anomaly_trainer.py
-----------------------------------------------
Unsupervised Real-Time Anomaly Detection Pipeline (Stage 8D — Problem A):
- Question: "Is this machine behaving abnormally at time T?"
- Multi-Sensor Statistical Z-Score Baseline (Z > 3.0)
- Robust IQR / MAD Baseline (1.5 * IQR)
- Isolation Forest Anomaly Detection (contamination=0.03)
- Evaluates detection rate, false-positive rate, precision, recall, alert frequency, and score stability
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import precision_score, recall_score, f1_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from data_science.db import load_telemetry_features


class MachineAnomalyPipeline:
    """
    Unsupervised Anomaly Detection Pipeline for Machine Telemetry.
    """

    def __init__(self, contamination: float = 0.03, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.sensor_cols = ["avg_temperature_c", "avg_vibration_rms", "avg_pressure_psi", "avg_power_kw"]

    def load_data(self) -> pd.DataFrame:
        df = load_telemetry_features()
        # Clean missing values
        df = df.dropna(subset=self.sensor_cols).reset_index(drop=True)
        return df

    def compute_zscore_baseline(self, df: pd.DataFrame, z_threshold: float = 3.0) -> np.ndarray:
        """
        Multi-sensor Z-Score baseline: Flag = 1 if max(|Z|) > z_threshold across any sensor.
        """
        z_scores = np.zeros((len(df), len(self.sensor_cols)))
        for i, col in enumerate(self.sensor_cols):
            mean_val = df[col].mean()
            std_val = df[col].std() + 1e-5
            z_scores[:, i] = np.abs((df[col] - mean_val) / std_val)
        
        max_z = np.max(z_scores, axis=1)
        return (max_z > z_threshold).astype(int), max_z

    def compute_iqr_baseline(self, df: pd.DataFrame, iqr_multiplier: float = 1.5) -> np.ndarray:
        """
        Robust IQR / MAD baseline: Flag = 1 if value falls outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
        """
        anom_flags = np.zeros(len(df), dtype=int)
        for col in self.sensor_cols:
            q25 = df[col].quantile(0.25)
            q75 = df[col].quantile(0.75)
            iqr = q75 - q25
            lower_bound = q25 - iqr_multiplier * iqr
            upper_bound = q75 + iqr_multiplier * iqr
            anom_flags |= ((df[col] < lower_bound) | (df[col] > upper_bound)).astype(int)
        return anom_flags

    def train_isolation_forest(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, IsolationForest]:
        """
        Fit Isolation Forest on scaled multi-sensor telemetry features.
        Returns: binary predictions (1 = anomaly, 0 = normal), continuous anomaly scores, fitted model.
        """
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(df[self.sensor_cols])

        iso = IsolationForest(
            contamination=self.contamination,
            n_estimators=150,
            random_state=self.random_state,
            n_jobs=-1
        )
        # raw_preds: -1 for anomaly, 1 for inlier
        raw_preds = iso.fit_predict(X_scaled)
        preds = (raw_preds == -1).astype(int)

        # score_samples returns negative anomaly score (lower means more anomalous)
        raw_scores = iso.score_samples(X_scaled)
        # Normalize continuous anomaly score to [0, 1] range
        anomaly_scores = (raw_scores.max() - raw_scores) / (raw_scores.max() - raw_scores.min() + 1e-5)

        return preds, anomaly_scores, iso

    def evaluate_all_anomaly_methods(self, df: pd.DataFrame) -> dict:
        """
        Evaluate Z-Score, IQR, and Isolation Forest against ground truth degradation/high-anomaly score.
        """
        # Ground truth pseudo-label: anomaly_severity_score > 0.50
        y_ground_truth = (df["anomaly_severity_score"] > 0.50).astype(int).values
        n_ground_truth = int(np.sum(y_ground_truth))

        # 1. Z-Score Baseline
        z_preds, max_z = self.compute_zscore_baseline(df, z_threshold=3.0)
        
        # 2. IQR Baseline
        iqr_preds = self.compute_iqr_baseline(df, iqr_multiplier=1.5)

        # 3. Isolation Forest
        iso_preds, iso_scores, _ = self.train_isolation_forest(df)

        n_machines = df["machine_id"].nunique()
        n_days = (df["minute_timestamp"].max() - df["minute_timestamp"].min()).days + 1

        results = {
            "Statistical_ZScore_Baseline": {
                "detected_anomalies": int(np.sum(z_preds)),
                "detection_rate": float(np.mean(z_preds)),
                "alerts_per_machine_day": float(np.sum(z_preds) / (n_machines * n_days)),
                "precision": float(precision_score(y_ground_truth, z_preds, zero_division=0)),
                "recall": float(recall_score(y_ground_truth, z_preds, zero_division=0)),
                "f1": float(f1_score(y_ground_truth, z_preds, zero_division=0))
            },
            "Robust_IQR_Baseline": {
                "detected_anomalies": int(np.sum(iqr_preds)),
                "detection_rate": float(np.mean(iqr_preds)),
                "alerts_per_machine_day": float(np.sum(iqr_preds) / (n_machines * n_days)),
                "precision": float(precision_score(y_ground_truth, iqr_preds, zero_division=0)),
                "recall": float(recall_score(y_ground_truth, iqr_preds, zero_division=0)),
                "f1": float(f1_score(y_ground_truth, iqr_preds, zero_division=0))
            },
            "Isolation_Forest_Detector": {
                "detected_anomalies": int(np.sum(iso_preds)),
                "detection_rate": float(np.mean(iso_preds)),
                "alerts_per_machine_day": float(np.sum(iso_preds) / (n_machines * n_days)),
                "precision": float(precision_score(y_ground_truth, iso_preds, zero_division=0)),
                "recall": float(recall_score(y_ground_truth, iso_preds, zero_division=0)),
                "f1": float(f1_score(y_ground_truth, iso_preds, zero_division=0))
            }
        }
        return results, (z_preds, iqr_preds, iso_preds, iso_scores)
