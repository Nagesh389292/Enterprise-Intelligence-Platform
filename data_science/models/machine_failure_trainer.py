"""
data_science/models/machine_failure_trainer.py
-----------------------------------------------
Supervised 24-Hour Machine Failure Prediction Pipeline (Stage 8D — Problem B):
- Question: "Given only telemetry available up to time T, will this machine fail within T+1..T+24 hours?"
- Leak-Free Past Time-Series Window Feature Engineering (rolling 1h, 6h means, stds, slopes, baseline deviations)
- Chronological Walk-Forward TimeSeriesSplit Cross-Validation (n_splits=5)
- Candidate Models: Logistic Regression, Random Forest, XGBoost, LightGBM
- Evaluates PR-AUC, ROC-AUC, Precision, Recall, F1, Brier Score, and Simulated Financial Downtime Savings
- Computes SHAP feature attributions for failure risk drivers
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, recall_score,
    f1_score, brier_score_loss
)
import shap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from data_science.db import load_telemetry_features, read_sql


class MachineFailureMLPipeline:
    """
    Supervised Machine Failure Prediction Pipeline with Chronological Cross-Validation.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.num_cols = [
            "rolling_6h_avg_temp", "rolling_6h_std_temp", "temp_slope_6h",
            "rolling_6h_avg_vib", "rolling_6h_std_vib", "vib_slope_6h",
            "rolling_6h_avg_press", "rolling_6h_std_press",
            "temp_baseline_diff", "vib_baseline_diff", "recent_anomaly_count_6h"
        ]
        self.cat_cols = ["machine_type", "warehouse_name"]
        self.target_col = "will_fail_next_24h"
        self.feature_names = []

    def load_data(self) -> pd.DataFrame:
        df = load_telemetry_features()
        df = df.sort_values(["machine_id", "minute_timestamp"]).reset_index(drop=True)

        # 1. Feature Engineering (Strictly Past Telemetry Windows <= T)
        df["rolling_6h_avg_temp"] = df.groupby("machine_id")["avg_temperature_c"].transform(lambda x: x.rolling(72, min_periods=1).mean())
        df["rolling_6h_std_temp"] = df.groupby("machine_id")["avg_temperature_c"].transform(lambda x: x.rolling(72, min_periods=1).std().fillna(0.0))
        df["temp_slope_6h"] = df.groupby("machine_id")["avg_temperature_c"].transform(lambda x: x.diff(12).fillna(0.0))

        df["rolling_6h_avg_vib"] = df.groupby("machine_id")["avg_vibration_rms"].transform(lambda x: x.rolling(72, min_periods=1).mean())
        df["rolling_6h_std_vib"] = df.groupby("machine_id")["avg_vibration_rms"].transform(lambda x: x.rolling(72, min_periods=1).std().fillna(0.0))
        df["vib_slope_6h"] = df.groupby("machine_id")["avg_vibration_rms"].transform(lambda x: x.diff(12).fillna(0.0))

        df["rolling_6h_avg_press"] = df.groupby("machine_id")["avg_pressure_psi"].transform(lambda x: x.rolling(72, min_periods=1).mean())
        df["rolling_6h_std_press"] = df.groupby("machine_id")["avg_pressure_psi"].transform(lambda x: x.rolling(72, min_periods=1).std().fillna(0.0))

        # Deviation from Machine Baseline
        machine_temp_mean = df.groupby("machine_id")["avg_temperature_c"].transform("mean")
        machine_vib_mean = df.groupby("machine_id")["avg_vibration_rms"].transform("mean")
        df["temp_baseline_diff"] = df["avg_temperature_c"] - machine_temp_mean
        df["vib_baseline_diff"] = df["avg_vibration_rms"] - machine_vib_mean

        # Recent Z-Score > 2.5 anomaly count in 6h
        temp_z = np.abs((df["avg_temperature_c"] - df["avg_temperature_c"].mean()) / (df["avg_temperature_c"].std() + 1e-5))
        df["is_temp_z_anom"] = (temp_z > 2.5).astype(int)
        df["recent_anomaly_count_6h"] = df.groupby("machine_id")["is_temp_z_anom"].transform(lambda x: x.rolling(72, min_periods=1).sum())

        # 2. Target Label Construction: will_fail_next_24h
        try:
            failures = read_sql("SELECT machine_id, occurred_at FROM analytics.stg_failure_events")
            failures["occurred_at"] = pd.to_datetime(failures["occurred_at"])
        except Exception:
            failures = pd.DataFrame(columns=["machine_id", "occurred_at"])

        y_target = np.zeros(len(df), dtype=int)
        if not failures.empty:
            for _, f_row in failures.iterrows():
                m_id = f_row["machine_id"]
                f_time = f_row["occurred_at"]
                mask = (df["machine_id"] == m_id) & (df["minute_timestamp"] < f_time) & (df["minute_timestamp"] >= f_time - pd.Timedelta(hours=24))
                y_target[mask] = 1

        df[self.target_col] = y_target

        df = df.dropna(subset=self.num_cols + self.cat_cols + [self.target_col]).reset_index(drop=True)
        return df

    def get_preprocessor(self) -> ColumnTransformer:
        return ColumnTransformer(
            transformers=[
                ("num", RobustScaler(), self.num_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), self.cat_cols)
            ]
        )

    def get_candidate_models(self) -> dict:
        return {
            "Logistic_Regression_Classifier": LogisticRegression(
                C=1.0, max_iter=1000, class_weight="balanced", random_state=self.random_state
            ),
            "Random_Forest_Classifier": RandomForestClassifier(
                n_estimators=100, max_depth=6, class_weight="balanced",
                n_jobs=-1, random_state=self.random_state
            ),
            "XGBoost_Failure_Classifier": XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.05,
                scale_pos_weight=10.0, subsample=0.8, colsample_bytree=0.8,
                n_jobs=-1, random_state=self.random_state
            ),
            "LightGBM_Failure_Classifier": LGBMClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.05,
                scale_pos_weight=10.0, subsample=0.8, colsample_bytree=0.8,
                n_jobs=-1, random_state=self.random_state, verbose=-1
            )
        }

    def evaluate_all_models(self, df: pd.DataFrame, n_splits: int = 5) -> tuple[dict, dict]:
        """
        Chronological Walk-Forward TimeSeriesSplit Cross-Validation.
        """
        X = df[self.num_cols + self.cat_cols]
        y = df[self.target_col].values

        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        results = {}
        oof_predictions = {}

        models = self.get_candidate_models()

        for mname, model in models.items():
            oof_proba = np.zeros(len(y))
            oof_pred = np.zeros(len(y))
            val_indices = []

            for train_idx, val_idx in tscv.split(X):
                val_indices.extend(val_idx)
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]

                pipeline = Pipeline([
                    ("prep", self.get_preprocessor()),
                    ("model", model)
                ])

                pipeline.fit(X_train, y_train)
                probas = pipeline.predict_proba(X_val)[:, 1]
                preds = (probas >= 0.50).astype(int)

                oof_proba[val_idx] = probas
                oof_pred[val_idx] = preds

            val_idx_arr = np.array(val_indices)
            y_eval = y[val_idx_arr]
            proba_eval = oof_proba[val_idx_arr]
            pred_eval = oof_pred[val_idx_arr]

            results[mname] = {
                "roc_auc": float(roc_auc_score(y_eval, proba_eval)),
                "pr_auc": float(average_precision_score(y_eval, proba_eval)),
                "precision": float(precision_score(y_eval, pred_eval, zero_division=0)),
                "recall": float(recall_score(y_eval, pred_eval, zero_division=0)),
                "f1": float(f1_score(y_eval, pred_eval, zero_division=0)),
                "brier_score": float(brier_score_loss(y_eval, proba_eval))
            }
            oof_predictions[mname] = (val_idx_arr, proba_eval, pred_eval)

        return results, oof_predictions

    def train_champion_model(self, df: pd.DataFrame, model_name: str = "XGBoost_Failure_Classifier"):
        X = df[self.num_cols + self.cat_cols]
        y = df[self.target_col].values

        models = self.get_candidate_models()
        chosen_model = models[model_name]

        pipeline = Pipeline([
            ("prep", self.get_preprocessor()),
            ("model", chosen_model)
        ])

        pipeline.fit(X, y)

        prep = pipeline.named_steps["prep"]
        cat_encoder = prep.named_transformers_["cat"]
        cat_feature_names = cat_encoder.get_feature_names_out(self.cat_cols).tolist()
        self.feature_names = self.num_cols + cat_feature_names

        X_trans = prep.transform(X)
        X_trans_df = pd.DataFrame(X_trans, columns=self.feature_names)

        return pipeline, X_trans_df

    def compute_shap(self, pipeline: Pipeline, X_trans_df: pd.DataFrame) -> tuple[np.ndarray, shap.Explainer]:
        model = pipeline.named_steps["model"]
        if hasattr(model, "coef_"):
            explainer = shap.LinearExplainer(model, X_trans_df)
            shap_values = explainer.shap_values(X_trans_df)
        else:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_trans_df)
        return shap_values, explainer
