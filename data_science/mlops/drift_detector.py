"""
Data Drift, Prediction Drift & Model Performance Monitoring Engine
===================================================================
Executes statistical feature drift (KS-Test, PSI) and prediction drift audits
between baseline training distributions and current scoring batches.
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from scipy import stats

from data_science.db import get_engine, read_sql, load_churn_features, load_demand_features, load_inventory_features

logger = logging.getLogger(__name__)

def calculate_psi(baseline: np.ndarray, current: np.ndarray, num_bins: int = 10) -> float:
    """
    Calculates Population Stability Index (PSI) between baseline and current distributions.
    """
    baseline = baseline[~np.isnan(baseline)]
    current = current[~np.isnan(current)]
    
    if len(baseline) == 0 or len(current) == 0:
        return 0.0

    # Determine quantiles based on baseline
    quantiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(baseline, quantiles)
    bins[0] = -np.inf
    bins[-1] = np.inf
    
    # Handle duplicate bin edges
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0

    baseline_counts, _ = np.histogram(baseline, bins=bins)
    current_counts, _ = np.histogram(current, bins=bins)

    baseline_pct = baseline_counts / len(baseline)
    current_pct = current_counts / len(current)

    # Avoid zero division
    baseline_pct = np.where(baseline_pct == 0, 0.0001, baseline_pct)
    current_pct = np.where(current_pct == 0, 0.0001, current_pct)

    psi_val = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    return float(psi_val)

class DriftDetector:
    """
    Statistical drift monitoring engine evaluating KS-test p-values and PSI scores
    across features and predictions.
    """
    def __init__(self, db_engine=None):
        self.engine = db_engine or get_engine()

    def run_drift_audit(self) -> Dict[str, Any]:
        """
        Runs comprehensive data and prediction drift audits across all 4 domains.
        """
        audit_results = {
            "audit_timestamp": pd.Timestamp.now().isoformat(),
            "domains": {}
        }

        audit_results["domains"]["customer_churn"] = self._audit_domain_drift(
            data_loader=load_churn_features,
            pred_table="analytics.fact_predictions_customer_churn",
            target_col="churn_probability"
        )

        audit_results["domains"]["sku_demand"] = self._audit_domain_drift(
            data_loader=load_demand_features,
            pred_table="analytics.fact_predictions_sku_demand",
            target_col="predicted_demand_units"
        )

        audit_results["domains"]["inventory_stockout"] = self._audit_domain_drift(
            data_loader=load_inventory_features,
            pred_table="analytics.fact_predictions_inventory_stockout",
            target_col="stockout_risk_prob_7d"
        )

        # Save to JSON
        output_dir = "docs/mlops"
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "drift_report.json")

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(audit_results, f, indent=2)

        logger.info(f"Saved drift monitoring report to {report_path}.")
        return audit_results

    def _audit_domain_drift(
        self,
        data_loader,
        pred_table: str,
        target_col: str
    ) -> Dict[str, Any]:
        """
        Splits data into 50% baseline (historical) vs 50% current (recent)
        and measures feature & prediction drift.
        """
        try:
            df_gold = data_loader()
            df_pred = read_sql(f"SELECT * FROM {pred_table};", self.engine)
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

        if df_gold.empty or df_pred.empty:
            return {"status": "SKIPPED", "reason": "Insufficient data"}

        # Numerical columns only
        num_cols = df_gold.select_dtypes(include=[np.number]).columns.tolist()
        num_cols = [c for c in num_cols if c not in ["customer_id", "product_id", "item_id", "machine_id"]]

        # Split 50% baseline vs 50% current
        split_idx = len(df_gold) // 2
        df_base = df_gold.iloc[:split_idx]
        df_curr = df_gold.iloc[split_idx:]

        feature_drifts = []
        retrain_triggers = []

        for col in num_cols:
            base_vals = df_base[col].dropna().values
            curr_vals = df_curr[col].dropna().values

            if len(base_vals) < 5 or len(curr_vals) < 5:
                continue

            ks_stat, ks_pval = stats.ks_2samp(base_vals, curr_vals)
            psi_val = calculate_psi(base_vals, curr_vals)

            drift_flag = bool(psi_val >= 0.25 or ks_pval < 0.01)
            if drift_flag:
                retrain_triggers.append(col)

            feature_drifts.append({
                "feature_name": col,
                "ks_statistic": float(ks_stat),
                "ks_pvalue": float(ks_pval),
                "psi_score": float(psi_val),
                "drift_detected": drift_flag
            })

        # Prediction Drift Audit
        pred_vals = df_pred[target_col].dropna().values
        pred_psi = calculate_psi(pred_vals[:len(pred_vals)//2], pred_vals[len(pred_vals)//2:]) if len(pred_vals) >= 10 else 0.0

        retrain_recommended = len(retrain_triggers) > 0 or pred_psi >= 0.25

        return {
            "status": "COMPLETED",
            "total_features_audited": len(feature_drifts),
            "drifted_features_count": len(retrain_triggers),
            "prediction_psi_score": float(pred_psi),
            "retraining_recommended": retrain_recommended,
            "feature_details": feature_drifts[:10] # Top 10 audited features
        }

    def detect_domain_drift(self, domain: str) -> Dict[str, Any]:
        """
        Check if drift is detected for a specific domain.
        Returns dict with has_drift boolean and max_psi score.
        """
        domain_clean = domain.lower().strip()
        domain_map = {
            "churn": (load_churn_features, "analytics.fact_predictions_customer_churn", "churn_probability"),
            "demand": (load_demand_features, "analytics.fact_predictions_sku_demand", "predicted_demand_units"),
            "stockout": (load_inventory_features, "analytics.fact_predictions_inventory_stockout", "stockout_risk_prob_7d"),
            "machine_health": (load_churn_features, "analytics.fact_predictions_machine_health", "failure_prob_24h"),
        }

        if domain_clean not in domain_map:
            return {"has_drift": False, "max_psi": 0.0, "reason": f"Unknown domain {domain}"}

        loader, ptable, tcol = domain_map[domain_clean]
        res = self._audit_domain_drift(loader, ptable, tcol)
        
        has_drift = res.get("retraining_recommended", False)
        max_psi = res.get("prediction_psi_score", 0.0)

        return {
            "has_drift": has_drift,
            "max_psi": max_psi,
            "details": res,
        }

