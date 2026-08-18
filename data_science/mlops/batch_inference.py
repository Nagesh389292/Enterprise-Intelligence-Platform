"""
Production Prediction Store & Automated Batch Inference Engine
===============================================================
Executes automated batch predictions across Gold datasets for all 4 baseline ML models
and persists results into PostgreSQL prediction tables in the analytics schema.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np
import joblib
from sqlalchemy import text

from data_science.db import get_engine, read_sql, load_churn_features, load_demand_features, load_inventory_features, load_telemetry_features
from data_science.mlops.registry import ModelRegistryManager

logger = logging.getLogger(__name__)

def extract_model_meta(loaded_obj: Any, default_threshold: float = 0.5) -> Tuple[Any, Optional[List[str]], float, str]:
    """Helper to extract model object, feature columns, threshold, and run_id."""
    if isinstance(loaded_obj, dict):
        model = loaded_obj.get("model", loaded_obj)
        feature_cols = loaded_obj.get("feature_cols", getattr(model, "feature_names_in_", None))
        threshold = loaded_obj.get("optimal_threshold", default_threshold)
        run_id = loaded_obj.get("mlflow_run_id", "local_champion")
    else:
        model = loaded_obj
        feature_cols = list(getattr(model, "feature_names_in_", [])) if hasattr(model, "feature_names_in_") else None
        threshold = default_threshold
        run_id = "local_champion"

    if feature_cols is not None:
        feature_cols = [str(c) for c in feature_cols]
    return model, feature_cols, threshold, run_id


def build_failure_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the 13 features the Stage 8D champion Random Forest was trained on.

    The model's feature_names_in_ are:
        rolling_6h_avg_temp, rolling_6h_std_temp, temp_slope_6h,
        rolling_6h_avg_vib,  rolling_6h_std_vib,  vib_slope_6h,
        rolling_6h_avg_press, rolling_6h_std_press,
        temp_baseline_diff, vib_baseline_diff,
        recent_anomaly_count_6h,
        machine_type, warehouse_name

    The Gold table (ml_machine_telemetry_features) only stores 10-minute rolling
    windows; this function recomputes the 6-hour equivalents at inference time
    using a backward-looking rolling window over the minute-level rows.

    Window size: 6h at 5-min cadence = 72 rows per machine.
    """
    WINDOW = 72  # 6 hours of 5-minute intervals

    # Ensure the dataframe is sorted correctly before group-wise rolling
    df = df.sort_values(["machine_id", "minute_timestamp"]).copy()
    df["minute_timestamp"] = pd.to_datetime(df["minute_timestamp"], utc=True)

    # ------------------------------------------------------------------ #
    # 6-hour rolling statistics (strictly backward-looking, min_periods=1)
    # ------------------------------------------------------------------ #
    def rolling_stats(group: pd.DataFrame) -> pd.DataFrame:
        temp = group["avg_temperature_c"]
        vib  = group["avg_vibration_rms"]
        press = group["avg_pressure_psi"]
        anom_flag = group["anomaly_severity_score"].gt(0.5).astype(int)

        g = group.copy()

        # Means
        g["rolling_6h_avg_temp"]  = temp.rolling(WINDOW, min_periods=1).mean()
        g["rolling_6h_avg_vib"]   = vib.rolling(WINDOW, min_periods=1).mean()
        g["rolling_6h_avg_press"] = press.rolling(WINDOW, min_periods=1).mean()

        # Standard deviations (ddof=0 avoids NaN for small windows)
        g["rolling_6h_std_temp"]  = temp.rolling(WINDOW, min_periods=2).std(ddof=0).fillna(0.0)
        g["rolling_6h_std_vib"]   = vib.rolling(WINDOW, min_periods=2).std(ddof=0).fillna(0.0)
        g["rolling_6h_std_press"] = press.rolling(WINDOW, min_periods=2).std(ddof=0).fillna(0.0)

        # Slopes via linear regression approximation over the window
        # Use difference from rolling mean as a lightweight slope proxy:
        #   slope ≈ (current - rolling_mean) / (window/2)
        half = max(WINDOW / 2.0, 1.0)
        g["temp_slope_6h"] = (temp - g["rolling_6h_avg_temp"]) / half
        g["vib_slope_6h"]  = (vib  - g["rolling_6h_avg_vib"])  / half

        # Baseline diffs: deviation from the per-machine global mean
        # (computed once per group)
        machine_mean_temp = temp.mean()
        machine_mean_vib  = vib.mean()
        g["temp_baseline_diff"] = temp - machine_mean_temp
        g["vib_baseline_diff"]  = vib  - machine_mean_vib

        # Recent anomaly count in 6h window
        g["recent_anomaly_count_6h"] = anom_flag.rolling(WINDOW, min_periods=1).sum()

        return g

    logger.info("build_failure_features: computing 6h rolling stats per machine...")
    result = df.groupby("machine_id", group_keys=False).apply(
        rolling_stats, include_groups=False
    )
    # restore machine_id column (excluded by include_groups=False)
    result = result.reset_index()
    if "machine_id" not in result.columns:
        # fallback: re-merge from df
        result = df[["machine_id"]].reset_index(drop=True).join(result.reset_index(drop=True))
    logger.info("build_failure_features: done (%d rows).", len(result))
    return result


class BatchInferenceEngine:
    """
    Production batch inference orchestrator loading registered models (or fallbacks),
    executing batch predictions, and persisting structured records to PostgreSQL.
    """
    def __init__(self, db_engine=None):
        self.engine = db_engine or get_engine()
        self.registry = ModelRegistryManager()

    def run_all_batch_inferences(self) -> Dict[str, Any]:
        """
        Executes batch inference pipelines for all 4 ML domains.
        Returns a summary report of records written per table.
        """
        results = {}
        results["churn"] = self.run_churn_batch_inference()
        results["demand"] = self.run_demand_batch_inference()
        results["stockout"] = self.run_stockout_batch_inference()
        results["machine_health"] = self.run_machine_health_batch_inference()
        return results

    # -------------------------------------------------------------------------
    # 1. Customer Churn Batch Inference (Stage 8A)
    # -------------------------------------------------------------------------
    def run_churn_batch_inference(self) -> Dict[str, Any]:
        logger.info("Executing Customer Churn Batch Inference...")
        
        df = load_churn_features()
        if df.empty:
            return {"status": "SKIPPED", "reason": "ml_customer_churn_features empty"}

        model_path = "models/churn/champion_churn_model.pkl"
        if not os.path.exists(model_path):
            return {"status": "SKIPPED", "reason": f"Model artifact not found at {model_path}"}
        
        loaded_obj = joblib.load(model_path)
        model, feature_cols, threshold, run_id = extract_model_meta(loaded_obj, default_threshold=0.11)

        X = df[feature_cols].copy() if feature_cols else df.copy()

        probs = model.predict_proba(X)[:, 1]
        preds = (probs >= threshold).astype(int)

        records = []
        now_ts = datetime.now(timezone.utc)
        for i, row in df.iterrows():
            p = float(probs[i])
            f = int(preds[i])
            tier = "High" if p >= threshold else ("Medium" if p >= 0.05 else "Low")
            records.append({
                "prediction_id": str(uuid.uuid4()),
                "customer_id": str(row["customer_id"]),
                "prediction_timestamp": now_ts,
                "churn_probability": p,
                "predicted_churn_flag": f,
                "risk_tier": tier,
                "model_version": "v1.0.0_XGBoost",
                "run_id": str(run_id),
                "created_at": now_ts
            })

        pred_df = pd.DataFrame(records)
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM analytics.fact_predictions_customer_churn;"))
            pred_df.to_sql("fact_predictions_customer_churn", conn, schema="analytics", if_exists="append", index=False)

        logger.info(f"Successfully wrote {len(pred_df)} records to analytics.fact_predictions_customer_churn.")
        return {"status": "SUCCESS", "records_written": len(pred_df)}

    # -------------------------------------------------------------------------
    # 2. SKU Demand Batch Inference (Stage 8B)
    # -------------------------------------------------------------------------
    def run_demand_batch_inference(self) -> Dict[str, Any]:
        logger.info("Executing SKU Demand Batch Inference...")

        df = load_demand_features()
        if df.empty:
            return {"status": "SKIPPED", "reason": "ml_demand_forecasting_daily empty"}

        model_path = "models/demand/champion_demand_model.pkl"
        if not os.path.exists(model_path):
            return {"status": "SKIPPED", "reason": f"Model artifact not found at {model_path}"}

        loaded_obj = joblib.load(model_path)
        model, feature_cols, _, run_id = extract_model_meta(loaded_obj)
        rmse = 8.81

        # Check required columns
        if feature_cols:
            for c in feature_cols:
                if c not in df.columns:
                    df[c] = 0.0
            X = df[feature_cols].fillna(0).copy()
        else:
            X = df.select_dtypes(include=[np.number]).fillna(0).copy()

        preds = model.predict(X)
        preds = np.clip(preds, 0, None)

        records = []
        now_ts = datetime.now(timezone.utc)
        for i, row in df.iterrows():
            pred_val = float(preds[i])
            records.append({
                "prediction_id": str(uuid.uuid4()),
                "product_id": str(row["product_id"]),
                "forecast_date": pd.to_datetime(row["sale_date"]).date(),
                "prediction_timestamp": now_ts,
                "predicted_demand_units": pred_val,
                "lower_bound_95": max(0.0, pred_val - 1.96 * rmse),
                "upper_bound_95": pred_val + 1.96 * rmse,
                "model_version": "v1.0.0_Ridge",
                "run_id": str(run_id),
                "created_at": now_ts
            })

        pred_df = pd.DataFrame(records)
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM analytics.fact_predictions_sku_demand;"))
            pred_df.to_sql("fact_predictions_sku_demand", conn, schema="analytics", if_exists="append", index=False)

        logger.info(f"Successfully wrote {len(pred_df)} records to analytics.fact_predictions_sku_demand.")
        return {"status": "SUCCESS", "records_written": len(pred_df)}

    # -------------------------------------------------------------------------
    # 3. Inventory Stockout Batch Inference (Stage 8C)
    # -------------------------------------------------------------------------
    def run_stockout_batch_inference(self) -> Dict[str, Any]:
        logger.info("Executing Inventory Stockout Batch Inference...")

        df = load_inventory_features()
        if df.empty:
            return {"status": "SKIPPED", "reason": "ml_inventory_stockout_risk empty"}

        model_path = "models/inventory/champion_stockout_model.pkl"
        if not os.path.exists(model_path):
            return {"status": "SKIPPED", "reason": f"Model artifact not found at {model_path}"}

        loaded_obj = joblib.load(model_path)
        model, feature_cols, threshold, run_id = extract_model_meta(loaded_obj, default_threshold=0.35)

        if feature_cols:
            for c in feature_cols:
                if c not in df.columns:
                    df[c] = 0.0
            X = df[feature_cols].copy()
        else:
            X = df.copy()

        probs = model.predict_proba(X)[:, 1]
        preds = (probs >= threshold).astype(int)

        records = []
        now_ts = datetime.now(timezone.utc)
        for i, row in df.iterrows():
            p = float(probs[i])
            f = int(preds[i])
            severity = "Critical" if p >= 0.50 else ("Moderate" if p >= 0.20 else "Low")
            records.append({
                "prediction_id": str(uuid.uuid4()),
                "item_id": str(row["inventory_id"]),
                "prediction_timestamp": now_ts,
                "stockout_risk_prob_7d": p,
                "stockout_alert_flag_7d": f,
                "risk_severity": severity,
                "model_version": "v1.0.0_XGBoost_7d",
                "run_id": str(run_id),
                "created_at": now_ts
            })

        pred_df = pd.DataFrame(records)
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM analytics.fact_predictions_inventory_stockout;"))
            pred_df.to_sql("fact_predictions_inventory_stockout", conn, schema="analytics", if_exists="append", index=False)

        logger.info(f"Successfully wrote {len(pred_df)} records to analytics.fact_predictions_inventory_stockout.")
        return {"status": "SUCCESS", "records_written": len(pred_df)}

    # -------------------------------------------------------------------------
    # 4. Machine Telemetry Batch Inference (Stage 8D)
    # -------------------------------------------------------------------------
    def run_machine_health_batch_inference(self) -> Dict[str, Any]:
        logger.info("Executing Machine Telemetry Batch Inference...")

        df = load_telemetry_features()
        if df.empty:
            return {"status": "SKIPPED", "reason": "ml_machine_telemetry_features empty"}

        anomaly_path = "models/telemetry/isolation_forest_anomaly_model.pkl"
        failure_path = "models/telemetry/champion_failure_model.pkl"

        if not os.path.exists(anomaly_path) or not os.path.exists(failure_path):
            return {"status": "SKIPPED", "reason": "Telemetry model artifacts not found"}

        anom_obj = joblib.load(anomaly_path)
        fail_obj = joblib.load(failure_path)

        fail_model, fail_cols, fail_thresh, run_id = extract_model_meta(fail_obj, default_threshold=0.50)

        if isinstance(anom_obj, dict):
            anom_model = anom_obj["model"]
            anom_scaler = anom_obj.get("scaler")
            anom_cols = anom_obj.get("feature_cols")
        else:
            anom_model = anom_obj
            anom_scaler = None
            anom_cols = None

        # Problem A: Anomaly
        if anom_cols:
            for c in anom_cols:
                if c not in df.columns:
                    df[c] = 0.0
            X_anom = df[anom_cols].copy()
        else:
            anom_cols = ["avg_temperature_c", "avg_vibration_rms", "avg_pressure_psi", "avg_power_kw"]
            for c in anom_cols:
                if c not in df.columns:
                    df[c] = 0.0
            X_anom = df[anom_cols].copy()

        if anom_scaler:
            X_anom_scaled = anom_scaler.transform(X_anom)
        else:
            X_anom_scaled = X_anom.values

        anom_scores = -anom_model.score_samples(X_anom_scaled)
        # Use percentile threshold matching the model's contamination (0.03 = top 3%).
        # IsolationForest.predict() over-flags when training/inference score distributions
        # differ; the percentile approach respects the intended anomaly rate.
        contamination = getattr(anom_model, "contamination", 0.03)
        anom_threshold = np.percentile(anom_scores, 100 * (1 - contamination))
        anom_preds = (anom_scores >= anom_threshold).astype(int)
        logger.info(
            "Anomaly scores: min=%.4f max=%.4f p97=%.4f flagged=%d/%d",
            anom_scores.min(), anom_scores.max(),
            anom_threshold, int(anom_preds.sum()), len(anom_preds),
        )

        # Problem B: Failure — build the 6h rolling features the model was trained on
        # The Gold table only has 10-min windows; build_failure_features() derives
        # all 11 missing rolling/slope/baseline columns from the raw minute-level data.
        df_with_fail_feats = build_failure_features(df)

        if fail_cols:
            for c in fail_cols:
                if c not in df_with_fail_feats.columns:
                    logger.warning("build_failure_features: column '%s' still missing — filling 0", c)
                    df_with_fail_feats[c] = 0.0
            X_fail = df_with_fail_feats[fail_cols].copy()
        else:
            logger.warning("Failure model has no feature_names_in_ — falling back to numeric columns")
            X_fail = df_with_fail_feats.select_dtypes(include=np.number).copy()

        # Re-align index so fail_probs maps correctly to the original df rows
        X_fail = X_fail.fillna(0.0)

        fail_probs = fail_model.predict_proba(X_fail)[:, 1]
        fail_preds = (fail_probs >= fail_thresh).astype(int)

        # df_with_fail_feats was sorted by (machine_id, minute_timestamp);
        # anom_scores / anom_preds were built from the ORIGINAL df ordering.
        # Re-align anomaly arrays onto the sorted index via a merge.
        df_orig_idx = df.reset_index(drop=True)
        df_sorted   = df_with_fail_feats.reset_index(drop=True)

        # Build anomaly score series on original df index for lookup
        anom_score_s = pd.Series(anom_scores, index=df_orig_idx.index)
        anom_pred_s  = pd.Series(anom_preds,  index=df_orig_idx.index)

        # Map (machine_id, minute_timestamp) → anomaly values
        key_cols = ["machine_id", "minute_timestamp"]
        df_orig_idx["_anom_score"] = anom_score_s.values
        df_orig_idx["_anom_pred"]  = anom_pred_s.values
        df_orig_idx["_key"] = df_orig_idx[key_cols].apply(
            lambda r: (str(r["machine_id"]), pd.Timestamp(r["minute_timestamp"])), axis=1
        )
        df_sorted["_key"] = df_sorted[key_cols].apply(
            lambda r: (str(r["machine_id"]), pd.Timestamp(r["minute_timestamp"])), axis=1
        )

        anom_lookup = dict(zip(df_orig_idx["_key"], zip(df_orig_idx["_anom_score"], df_orig_idx["_anom_pred"])))

        records = []
        now_ts = datetime.now(timezone.utc)
        for pos, (_, row) in enumerate(df_sorted.iterrows()):
            key = (str(row["machine_id"]), pd.Timestamp(row["minute_timestamp"]))
            anom_pair = anom_lookup.get(key, (0.0, 0))
            a_score = float(anom_pair[0])
            a_flag  = int(anom_pair[1])
            f_prob  = float(fail_probs[pos])
            f_flag  = int(fail_preds[pos])

            status_str = "Critical" if (f_flag == 1 or a_flag == 1) else (
                "Warning" if f_prob > 0.20 else "Normal"
            )

            records.append({
                "prediction_id":          str(uuid.uuid4()),
                "machine_id":             str(row["machine_id"]),
                "minute_timestamp":       pd.to_datetime(row["minute_timestamp"]),
                "prediction_timestamp":   now_ts,
                "anomaly_score":          a_score,
                "is_anomaly_flag":        a_flag,
                "failure_prob_24h":       f_prob,
                "failure_alert_flag_24h": f_flag,
                "health_status":          status_str,
                "model_version":          "v1.0.0_RF_IsolationForest",
                "run_id":                 str(run_id),
                "created_at":             now_ts,
            })

        pred_df = pd.DataFrame(records)
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM analytics.fact_predictions_machine_health;"))
            pred_df.to_sql("fact_predictions_machine_health", conn, schema="analytics", if_exists="append", index=False)

        logger.info(
            "Machine health inference: %d rows written. "
            "failure_prob range [%.4f, %.4f], mean=%.4f, non-zero=%d",
            len(pred_df),
            fail_probs.min(), fail_probs.max(), fail_probs.mean(),
            int((fail_probs > 0).sum()),
        )
        return {"status": "SUCCESS", "records_written": len(pred_df)}

