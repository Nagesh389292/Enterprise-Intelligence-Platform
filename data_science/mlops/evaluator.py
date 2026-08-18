"""
data_science/mlops/evaluator.py
===============================
Stage 11 — Champion vs. Challenger Evaluator & Promotion Gating Engine

Evaluates candidate models against current Production champion models on a holdout set
using domain-specific performance gates and strict no-regression rules.

Gate Criteria by Domain:
  1. Churn (8A):
     - PR-AUC_candidate >= PR-AUC_champion - 0.005 (no regression)
     - Recall@0.11 >= 0.65 (operating threshold gate)
  2. Demand (8B):
     - WAPE_candidate <= WAPE_champion + 0.005 (no regression)
     - RMSE_candidate <= RMSE_champion + 0.10 (no regression)
  3. Stockout (8C):
     - PR-AUC_candidate >= PR-AUC_champion - 0.005 (no regression)
     - F1@0.35 >= 0.70 (operating gate)
  4. Machine Health (8D):
     - Event-level 6h lead-time recall >= 0.66 (at least 2/3 failures warned >= 6h in advance)
     - PR-AUC_candidate >= PR-AUC_champion - 0.005 (no regression)
"""

import os
import sys
import logging
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, recall_score,
    f1_score, mean_squared_error, mean_absolute_error
)

from data_science.models.churn_trainer import ChurnMLPipeline
from data_science.models.demand_trainer import DemandMLPipeline
from data_science.models.inventory_stockout_trainer import InventoryStockoutMLPipeline
from data_science.models.machine_failure_trainer import MachineFailureMLPipeline

logger = logging.getLogger(__name__)

@dataclass
class EvaluationReport:
    domain: str
    passed_gate: bool
    champion_metrics: Dict[str, float]
    candidate_metrics: Dict[str, float]
    rationale: str
    details: Dict[str, Any]

class ModelEvaluator:
    """
    Champion vs. Challenger evaluator and promotion gating engine.
    """

    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir

    def evaluate_and_gate(self, domain: str, candidate_path: str) -> EvaluationReport:
        domain_clean = domain.lower().strip()
        if not os.path.exists(candidate_path):
            return EvaluationReport(
                domain=domain_clean,
                passed_gate=False,
                champion_metrics={},
                candidate_metrics={},
                rationale=f"Candidate artifact missing: {candidate_path}",
                details={}
            )

        if domain_clean == "churn":
            return self._evaluate_churn(candidate_path)
        elif domain_clean == "demand":
            return self._evaluate_demand(candidate_path)
        elif domain_clean == "stockout":
            return self._evaluate_stockout(candidate_path)
        elif domain_clean == "machine_health":
            return self._evaluate_machine_health(candidate_path)
        else:
            raise ValueError(f"Unknown domain: {domain}")

    # -------------------------------------------------------------------------
    # 1. Churn Gating
    # -------------------------------------------------------------------------
    def _evaluate_churn(self, candidate_path: str) -> EvaluationReport:
        champion_path = os.path.join(self.models_dir, "churn", "champion_churn_model.pkl")
        trainer = ChurnMLPipeline(random_state=42)
        X, y = trainer.load_data()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        cand_obj = joblib.load(candidate_path)
        cand_model = cand_obj.get("model", cand_obj) if isinstance(cand_obj, dict) else cand_obj
        cand_thresh = cand_obj.get("optimal_threshold", 0.11) if isinstance(cand_obj, dict) else 0.11

        cand_probs = cand_model.predict_proba(X_test)[:, 1]
        cand_preds = (cand_probs >= cand_thresh).astype(int)
        
        cand_metrics = {
            "pr_auc": float(average_precision_score(y_test, cand_probs)),
            "recall": float(recall_score(y_test, cand_preds, zero_division=0)),
            "precision": float(precision_score(y_test, cand_preds, zero_division=0)),
            "f1": float(f1_score(y_test, cand_preds, zero_division=0)),
        }

        champ_metrics = {}
        if os.path.exists(champion_path):
            champ_obj = joblib.load(champion_path)
            champ_model = champ_obj.get("model", champ_obj) if isinstance(champ_obj, dict) else champ_obj
            champ_thresh = champ_obj.get("optimal_threshold", 0.11) if isinstance(champ_obj, dict) else 0.11
            champ_probs = champ_model.predict_proba(X_test)[:, 1]
            champ_preds = (champ_probs >= champ_thresh).astype(int)
            champ_metrics = {
                "pr_auc": float(average_precision_score(y_test, champ_probs)),
                "recall": float(recall_score(y_test, champ_preds, zero_division=0)),
                "precision": float(precision_score(y_test, champ_preds, zero_division=0)),
                "f1": float(f1_score(y_test, champ_preds, zero_division=0)),
            }
        else:
            champ_metrics = {"pr_auc": 0.0, "recall": 0.0}

        pr_auc_pass = cand_metrics["pr_auc"] >= (champ_metrics.get("pr_auc", 0.0) - 0.005)
        recall_pass = cand_metrics["recall"] >= 0.65

        passed = pr_auc_pass and recall_pass
        rationale = []
        if pr_auc_pass:
            rationale.append(f"PR-AUC non-degrading ({cand_metrics['pr_auc']:.4f} >= {champ_metrics.get('pr_auc', 0.0):.4f} - 0.005)")
        else:
            rationale.append(f"PR-AUC regressed ({cand_metrics['pr_auc']:.4f} < {champ_metrics.get('pr_auc', 0.0):.4f})")

        if recall_pass:
            rationale.append(f"Recall@0.11 passed gate ({cand_metrics['recall']:.2%} >= 65.0%)")
        else:
            rationale.append(f"Recall@0.11 failed gate ({cand_metrics['recall']:.2%} < 65.0%)")

        return EvaluationReport(
            domain="churn",
            passed_gate=passed,
            champion_metrics=champ_metrics,
            candidate_metrics=cand_metrics,
            rationale=" | ".join(rationale),
            details={"candidate_threshold": cand_thresh}
        )

    # -------------------------------------------------------------------------
    # 2. Demand Gating
    # -------------------------------------------------------------------------
    def _evaluate_demand(self, candidate_path: str) -> EvaluationReport:
        champion_path = os.path.join(self.models_dir, "demand", "champion_demand_model.pkl")
        trainer = DemandMLPipeline(random_state=42)
        df_clean = trainer.load_data()

        split_idx = int(len(df_clean) * 0.8)
        df_test = df_clean.iloc[split_idx:].copy()
        X_test = df_test[trainer.num_cols + trainer.cat_cols]
        y_test = df_test[trainer.target_col].values

        cand_obj = joblib.load(candidate_path)
        cand_model = cand_obj.get("model", cand_obj) if isinstance(cand_obj, dict) else cand_obj
        cand_preds = np.clip(cand_model.predict(X_test), 0, None)

        cand_rmse = float(np.sqrt(mean_squared_error(y_test, cand_preds)))
        cand_wape = float(np.sum(np.abs(y_test - cand_preds)) / max(np.sum(y_test), 1.0))
        cand_metrics = {"rmse": cand_rmse, "wape": cand_wape}

        champ_metrics = {}
        if os.path.exists(champion_path):
            champ_obj = joblib.load(champion_path)
            champ_model = champ_obj.get("model", champ_obj) if isinstance(champ_obj, dict) else champ_obj
            champ_preds = np.clip(champ_model.predict(X_test), 0, None)
            champ_rmse = float(np.sqrt(mean_squared_error(y_test, champ_preds)))
            champ_wape = float(np.sum(np.abs(y_test - champ_preds)) / max(np.sum(y_test), 1.0))
            champ_metrics = {"rmse": champ_rmse, "wape": champ_wape}
        else:
            champ_metrics = {"rmse": 999.0, "wape": 999.0}

        wape_pass = cand_metrics["wape"] <= (champ_metrics.get("wape", 999.0) + 0.005)
        rmse_pass = cand_metrics["rmse"] <= (champ_metrics.get("rmse", 999.0) + 0.10)

        passed = wape_pass and rmse_pass
        rationale = []
        if wape_pass:
            rationale.append(f"WAPE non-degrading ({cand_metrics['wape']:.4f} <= {champ_metrics.get('wape', 999.0):.4f})")
        else:
            rationale.append(f"WAPE regressed ({cand_metrics['wape']:.4f} > {champ_metrics.get('wape', 999.0):.4f})")

        if rmse_pass:
            rationale.append(f"RMSE non-degrading ({cand_metrics['rmse']:.2f} <= {champ_metrics.get('rmse', 999.0):.2f})")
        else:
            rationale.append(f"RMSE regressed ({cand_metrics['rmse']:.2f} > {champ_metrics.get('rmse', 999.0):.2f})")

        return EvaluationReport(
            domain="demand",
            passed_gate=passed,
            champion_metrics=champ_metrics,
            candidate_metrics=cand_metrics,
            rationale=" | ".join(rationale),
            details={}
        )

    # -------------------------------------------------------------------------
    # 3. Stockout Gating
    # -------------------------------------------------------------------------
    def _evaluate_stockout(self, candidate_path: str) -> EvaluationReport:
        champion_path = os.path.join(self.models_dir, "inventory", "champion_stockout_model.pkl")
        trainer = InventoryStockoutMLPipeline(random_state=42)
        df_clean = trainer.load_data()

        X = df_clean[trainer.num_cols + trainer.cat_cols]
        y = df_clean[trainer.target_col_b]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        cand_obj = joblib.load(candidate_path)
        cand_model = cand_obj.get("model", cand_obj) if isinstance(cand_obj, dict) else cand_obj
        cand_thresh = cand_obj.get("optimal_threshold", 0.35) if isinstance(cand_obj, dict) else 0.35

        cand_probs = cand_model.predict_proba(X_test)[:, 1]
        cand_preds = (cand_probs >= cand_thresh).astype(int)

        cand_metrics = {
            "pr_auc": float(average_precision_score(y_test, cand_probs)),
            "f1": float(f1_score(y_test, cand_preds, zero_division=0)),
            "recall": float(recall_score(y_test, cand_preds, zero_division=0)),
            "precision": float(precision_score(y_test, cand_preds, zero_division=0)),
        }

        champ_metrics = {}
        if os.path.exists(champion_path):
            champ_obj = joblib.load(champion_path)
            champ_model = champ_obj.get("model", champ_obj) if isinstance(champ_obj, dict) else champ_obj
            champ_thresh = champ_obj.get("optimal_threshold", 0.35) if isinstance(champ_obj, dict) else 0.35
            champ_probs = champ_model.predict_proba(X_test)[:, 1]
            champ_preds = (champ_probs >= champ_thresh).astype(int)
            champ_metrics = {
                "pr_auc": float(average_precision_score(y_test, champ_probs)),
                "f1": float(f1_score(y_test, champ_preds, zero_division=0)),
                "recall": float(recall_score(y_test, champ_preds, zero_division=0)),
                "precision": float(precision_score(y_test, champ_preds, zero_division=0)),
            }
        else:
            champ_metrics = {"pr_auc": 0.0, "f1": 0.0}

        pr_auc_pass = cand_metrics["pr_auc"] >= (champ_metrics.get("pr_auc", 0.0) - 0.005)
        f1_pass = cand_metrics["f1"] >= 0.70

        passed = pr_auc_pass and f1_pass
        rationale = []
        if pr_auc_pass:
            rationale.append(f"PR-AUC non-degrading ({cand_metrics['pr_auc']:.4f} >= {champ_metrics.get('pr_auc', 0.0):.4f})")
        else:
            rationale.append(f"PR-AUC regressed ({cand_metrics['pr_auc']:.4f} < {champ_metrics.get('pr_auc', 0.0):.4f})")

        if f1_pass:
            rationale.append(f"F1@0.35 passed gate ({cand_metrics['f1']:.4f} >= 0.70)")
        else:
            rationale.append(f"F1@0.35 failed gate ({cand_metrics['f1']:.4f} < 0.70)")

        return EvaluationReport(
            domain="stockout",
            passed_gate=passed,
            champion_metrics=champ_metrics,
            candidate_metrics=cand_metrics,
            rationale=" | ".join(rationale),
            details={"candidate_threshold": cand_thresh}
        )

    # -------------------------------------------------------------------------
    # 4. Machine Health Gating (Includes Event-Level Lead-Time Recall)
    # -------------------------------------------------------------------------
    def _evaluate_machine_health(self, candidate_path: str) -> EvaluationReport:
        champion_path = os.path.join(self.models_dir, "telemetry", "champion_failure_model.pkl")
        trainer = MachineFailureMLPipeline(random_state=42)
        df_clean = trainer.load_data()

        split_idx = int(len(df_clean) * 0.8)
        df_test = df_clean.iloc[split_idx:].copy()
        X_test = df_test[trainer.num_cols + trainer.cat_cols]
        y_test = df_test[trainer.target_col].values

        cand_obj = joblib.load(candidate_path)
        cand_model = cand_obj.get("model", cand_obj) if isinstance(cand_obj, dict) else cand_obj
        cand_thresh = cand_obj.get("optimal_threshold", 0.50) if isinstance(cand_obj, dict) else 0.50

        cand_probs = cand_model.predict_proba(X_test)[:, 1]
        cand_preds = (cand_probs >= cand_thresh).astype(int)

        cand_metrics = {
            "pr_auc": float(average_precision_score(y_test, cand_probs)),
            "recall": float(recall_score(y_test, cand_preds, zero_division=0)),
            "precision": float(precision_score(y_test, cand_preds, zero_division=0)),
        }

        champ_metrics = {}
        if os.path.exists(champion_path):
            champ_obj = joblib.load(champion_path)
            champ_model = champ_obj.get("model", champ_obj) if isinstance(champ_obj, dict) else champ_obj
            champ_thresh = champ_obj.get("optimal_threshold", 0.50) if isinstance(champ_obj, dict) else 0.50
            champ_probs = champ_model.predict_proba(X_test)[:, 1]
            champ_preds = (champ_probs >= champ_thresh).astype(int)
            champ_metrics = {
                "pr_auc": float(average_precision_score(y_test, champ_probs)),
                "recall": float(recall_score(y_test, champ_preds, zero_division=0)),
                "precision": float(precision_score(y_test, champ_preds, zero_division=0)),
            }
        else:
            champ_metrics = {"pr_auc": 0.0, "recall": 0.0}

        # Event-level lead time audit check
        from data_science.db import read_sql
        failures = read_sql("SELECT machine_id, occurred_at FROM analytics.stg_failure_events")
        failures["occurred_at"] = pd.to_datetime(failures["occurred_at"])

        df_clean["cand_prob"] = cand_model.predict_proba(df_clean[trainer.num_cols + trainer.cat_cols])[:, 1]
        df_clean["cand_alert"] = (df_clean["cand_prob"] >= cand_thresh).astype(int)

        events_warned = 0
        for _, f_row in failures.iterrows():
            m_id = f_row["machine_id"]
            f_time = f_row["occurred_at"]
            w6h = df_clean[
                (df_clean["machine_id"] == m_id) &
                (df_clean["minute_timestamp"] >= f_time - pd.Timedelta(hours=24)) &
                (df_clean["minute_timestamp"] <= f_time - pd.Timedelta(hours=6))
            ]
            if w6h["cand_alert"].sum() > 0:
                events_warned += 1

        event_recall = events_warned / len(failures) if len(failures) > 0 else 0.0
        cand_metrics["event_recall_6h"] = round(event_recall, 4)

        pr_auc_pass = cand_metrics["pr_auc"] >= (champ_metrics.get("pr_auc", 0.0) - 0.005)
        event_recall_pass = event_recall >= 0.66

        passed = pr_auc_pass and event_recall_pass
        rationale = []
        if pr_auc_pass:
            rationale.append(f"PR-AUC non-degrading ({cand_metrics['pr_auc']:.4f} >= {champ_metrics.get('pr_auc', 0.0):.4f})")
        else:
            rationale.append(f"PR-AUC regressed ({cand_metrics['pr_auc']:.4f} < {champ_metrics.get('pr_auc', 0.0):.4f})")

        if event_recall_pass:
            rationale.append(f"Event-level 6h lead-time recall passed ({event_recall:.2%} >= 66.0%)")
        else:
            rationale.append(f"Event-level 6h lead-time recall failed ({event_recall:.2%} < 66.0%)")

        return EvaluationReport(
            domain="machine_health",
            passed_gate=passed,
            champion_metrics=champ_metrics,
            candidate_metrics=cand_metrics,
            rationale=" | ".join(rationale),
            details={"events_warned_6h": events_warned, "total_failures": len(failures)}
        )
