"""
data_science/mlops/retrain.py
==============================
Stage 11 — Domain-Aware Automated Retraining Engine

Executes targeted model retraining for a specific ML domain when drift is detected
or when requested via orchestration.

Supported domains:
  - churn          (Customer Churn XGBoost Classifier)
  - demand         (SKU Demand Ridge Regressor)
  - stockout       (Inventory Stockout Risk XGBoost Classifier)
  - machine_health (Machine Telemetry Failure Random Forest Pipeline)

Reuses exact feature extraction, preprocessing, and champion training logic from baseline trainers.
Logs candidate runs to MLflow and outputs structured candidate model artifacts.
"""

import os
import sys
import logging
import joblib
from pathlib import Path
from typing import Dict, Any

from data_science.models.churn_trainer import ChurnMLPipeline
from data_science.models.demand_trainer import DemandMLPipeline
from data_science.models.inventory_stockout_trainer import InventoryStockoutMLPipeline
from data_science.models.machine_failure_trainer import MachineFailureMLPipeline
from data_science.models.mlflow_utils import MLflowTracker
from data_science.mlops.registry import ModelRegistryManager

logger = logging.getLogger(__name__)

VALID_DOMAINS = ["churn", "demand", "stockout", "machine_health"]

class DomainRetrainer:
    """
    Domain-aware retraining manager.
    Retrains only the model for the requested domain, using authoritative feature logic,
    and returns candidate artifact metadata.
    """

    def __init__(self, output_dir: str = "models"):
        self.output_dir = Path(output_dir)
        self.registry = ModelRegistryManager()
        self.tracker = MLflowTracker(experiment_name="Domain_Retraining", tracking_uri="sqlite:///mlflow.db")

    def retrain_domain(self, domain: str) -> Dict[str, Any]:
        """
        Execute targeted retraining for a single domain.

        Args:
            domain: One of ['churn', 'demand', 'stockout', 'machine_health']

        Returns:
            Dict containing domain, candidate_path, metrics, and mlflow_run_id.
        """
        domain_clean = domain.lower().strip()
        if domain_clean not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain '{domain}'. Must be one of {VALID_DOMAINS}")

        logger.info("=" * 70)
        logger.info("Executing Targeted Retraining for Domain: %s", domain_clean.upper())
        logger.info("=" * 70)

        if domain_clean == "churn":
            return self._retrain_churn()
        elif domain_clean == "demand":
            return self._retrain_demand()
        elif domain_clean == "stockout":
            return self._retrain_stockout()
        elif domain_clean == "machine_health":
            return self._retrain_machine_health()

    # -------------------------------------------------------------------------
    # 1. Churn Retraining
    # -------------------------------------------------------------------------
    def _retrain_churn(self) -> Dict[str, Any]:
        trainer = ChurnMLPipeline(random_state=42)
        X, y = trainer.load_data()
        
        champion_name = "XGBoost_ScalePosWeight"
        pipeline, _ = trainer.train_champion_model(X, y, model_name=champion_name)
        
        candidate_dir = self.output_dir / "churn"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / "candidate_churn_model.pkl"

        optimal_thresh = 0.11
        artifact = {
            "model": pipeline,
            "feature_cols": trainer.num_cols + trainer.cat_cols,
            "optimal_threshold": optimal_thresh,
            "domain": "churn",
        }
        joblib.dump(artifact, candidate_path)

        metrics = {"status": "trained"}
        run_id = self.tracker.log_run(
            run_name="retrain_churn_candidate",
            params={"algorithm": champion_name, "domain": "churn"},
            metrics={"train_samples": len(y)},
            model_type="xgboost"
        )

        reg_info = self.registry.register_model_from_run(
            experiment_name="Domain_Retraining",
            model_name="candidate_churn_model",
            local_model_path=str(candidate_path),
            tags={"domain": "churn", "stage": "candidate"}
        )

        return {
            "domain": "churn",
            "candidate_path": str(candidate_path),
            "metrics": metrics,
            "mlflow_run_id": run_id,
            "version": reg_info.get("version"),
            "artifact": artifact,
        }

    # -------------------------------------------------------------------------
    # 2. Demand Retraining
    # -------------------------------------------------------------------------
    def _retrain_demand(self) -> Dict[str, Any]:
        trainer = DemandMLPipeline(random_state=42)
        df_clean = trainer.load_data()
        
        champion_name = "Ridge_Linear_Regressor"
        pipeline, _ = trainer.train_champion_model(df_clean, model_name=champion_name)

        candidate_dir = self.output_dir / "demand"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / "candidate_demand_model.pkl"

        artifact = {
            "model": pipeline,
            "feature_cols": trainer.num_cols + trainer.cat_cols,
            "domain": "demand",
        }
        joblib.dump(artifact, candidate_path)

        metrics = {"status": "trained"}
        run_id = self.tracker.log_run(
            run_name="retrain_demand_candidate",
            params={"algorithm": champion_name, "domain": "demand"},
            metrics={"train_samples": len(df_clean)},
            model_type="sklearn"
        )

        reg_info = self.registry.register_model_from_run(
            experiment_name="Domain_Retraining",
            model_name="candidate_demand_model",
            local_model_path=str(candidate_path),
            tags={"domain": "demand", "stage": "candidate"}
        )

        return {
            "domain": "demand",
            "candidate_path": str(candidate_path),
            "metrics": metrics,
            "mlflow_run_id": run_id,
            "version": reg_info.get("version"),
            "artifact": artifact,
        }

    # -------------------------------------------------------------------------
    # 3. Stockout Retraining
    # -------------------------------------------------------------------------
    def _retrain_stockout(self) -> Dict[str, Any]:
        trainer = InventoryStockoutMLPipeline(random_state=42)
        df_clean = trainer.load_data()

        champion_name = "XGBoost_Stockout_Classifier"
        pipeline, _ = trainer.train_champion_model(df_clean, target_col=trainer.target_col_b, model_name=champion_name)

        candidate_dir = self.output_dir / "inventory"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / "candidate_stockout_model.pkl"

        optimal_thresh = 0.35
        artifact = {
            "model": pipeline,
            "feature_cols": trainer.num_cols + trainer.cat_cols,
            "optimal_threshold": optimal_thresh,
            "domain": "stockout",
        }
        joblib.dump(artifact, candidate_path)

        metrics = {"status": "trained"}
        run_id = self.tracker.log_run(
            run_name="retrain_stockout_candidate",
            params={"algorithm": champion_name, "domain": "stockout"},
            metrics={"train_samples": len(df_clean)},
            model_type="xgboost"
        )

        reg_info = self.registry.register_model_from_run(
            experiment_name="Domain_Retraining",
            model_name="candidate_stockout_model",
            local_model_path=str(candidate_path),
            tags={"domain": "stockout", "stage": "candidate"}
        )

        return {
            "domain": "stockout",
            "candidate_path": str(candidate_path),
            "metrics": metrics,
            "mlflow_run_id": run_id,
            "version": reg_info.get("version"),
            "artifact": artifact,
        }

    # -------------------------------------------------------------------------
    # 4. Machine Health Retraining
    # -------------------------------------------------------------------------
    def _retrain_machine_health(self) -> Dict[str, Any]:
        trainer = MachineFailureMLPipeline(random_state=42)
        df_clean = trainer.load_data()

        champion_name = "RandomForest_Balanced"
        pipeline, _ = trainer.train_champion_model(df_clean, model_name=champion_name)

        candidate_dir = self.output_dir / "telemetry"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / "candidate_failure_model.pkl"

        optimal_thresh = 0.50
        artifact = {
            "model": pipeline,
            "feature_cols": trainer.num_cols + trainer.cat_cols,
            "optimal_threshold": optimal_thresh,
            "domain": "machine_health",
        }
        joblib.dump(artifact, candidate_path)

        metrics = {"status": "trained"}
        run_id = self.tracker.log_run(
            run_name="retrain_machine_health_candidate",
            params={"algorithm": champion_name, "domain": "machine_health"},
            metrics={"train_samples": len(df_clean)},
            model_type="sklearn"
        )

        reg_info = self.registry.register_model_from_run(
            experiment_name="Domain_Retraining",
            model_name="candidate_failure_model",
            local_model_path=str(candidate_path),
            tags={"domain": "machine_health", "stage": "candidate"}
        )

        return {
            "domain": "machine_health",
            "candidate_path": str(candidate_path),
            "metrics": metrics,
            "mlflow_run_id": run_id,
            "version": reg_info.get("version"),
            "artifact": artifact,
        }
