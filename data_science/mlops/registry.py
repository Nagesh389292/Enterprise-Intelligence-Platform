"""
MLflow Model Registry & Lifecycle Management Engine
===================================================
Manages model registration, versioning, stage promotion (Staging/Production/Archived),
and alias tagging using MLflow Client API.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"

class ModelRegistryManager:
    """
    Enterprise MLflow Model Registry manager supporting versioning, stage promotion,
    alias management, and artifact resolution.
    """
    def __init__(self, tracking_uri: str = DEFAULT_TRACKING_URI):
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def register_model_from_run(
        self,
        experiment_name: str,
        model_name: str,
        local_model_path: Optional[str] = None,
        artifact_path: str = "model",
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Finds the latest run in the specified experiment, registers the logged model artifact,
        and returns registration details. Auto-logs local model file if not present in MLflow run.
        """
        exp = self.client.get_experiment_by_name(experiment_name)
        if exp is None:
            # Create experiment if not found
            exp_id = self.client.create_experiment(experiment_name)
            exp = self.client.get_experiment(exp_id)

        runs = self.client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if not runs:
            # Start dummy run if none exist
            with mlflow.start_run(experiment_id=exp.experiment_id) as new_run:
                run_id = new_run.info.run_id
        else:
            run_id = runs[0].info.run_id

        # Check if model artifact exists in run, else log it
        artifacts = self.client.list_artifacts(run_id)
        has_model_art = any(a.path == artifact_path for a in artifacts)

        if not has_model_art and local_model_path and os.path.exists(local_model_path):
            import joblib
            model_obj = joblib.load(local_model_path)
            if isinstance(model_obj, dict):
                model_obj = model_obj.get("model", model_obj)
            with mlflow.start_run(run_id=run_id):
                try:
                    mlflow.sklearn.log_model(model_obj, artifact_path=artifact_path)
                except Exception:
                    mlflow.log_artifact(local_model_path, artifact_path=artifact_path)

        # Register model artifact
        model_uri = f"runs:/{run_id}/{artifact_path}"
        registered_version = mlflow.register_model(
            model_uri=model_uri,
            name=model_name,
            tags=tags or {"registered_by": "Stage9_MLOps_Pipeline"}
        )

        logger.info(f"Registered model '{model_name}' v{registered_version.version} from run '{run_id}'.")
        return {
            "model_name": model_name,
            "version": registered_version.version,
            "run_id": run_id,
            "experiment_name": experiment_name,
            "model_uri": model_uri
        }

    def promote_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str = "Production",
        archive_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Promotes a specific model version to target stage ('Production', 'Staging', 'Archived').
        Optionally archives previous versions in that stage.
        """
        valid_stages = ["Production", "Staging", "Archived", "None"]
        if stage not in valid_stages:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of {valid_stages}.")

        transitioned = self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing
        )

        # Set alias (e.g. 'production' alias)
        alias_name = stage.lower()
        if alias_name in ["production", "staging"]:
            self.client.set_registered_model_alias(
                name=model_name,
                alias=alias_name,
                version=version
            )

        logger.info(f"Promoted model '{model_name}' v{version} to stage '{stage}' (alias '@{alias_name}').")
        return {
            "model_name": model_name,
            "version": version,
            "current_stage": transitioned.current_stage,
            "alias": alias_name if alias_name in ["production", "staging"] else None
        }

    def get_production_model_uri(self, model_name: str) -> str:
        """
        Returns the MLflow URI for the current Production version of a model.
        Falls back to models:/<model_name>/Production or alias @production.
        """
        try:
            model_version_desc = self.client.get_model_version_by_alias(model_name, "production")
            return f"runs:/{model_version_desc.run_id}/model"
        except Exception:
            # Fallback to stage lookup
            latest_prod = self.client.get_latest_versions(model_name, stages=["Production"])
            if latest_prod:
                return f"runs:/{latest_prod[0].run_id}/model"
            raise RuntimeError(f"No Production version registered for model '{model_name}'.")

    def list_all_registered_models(self) -> List[Dict[str, Any]]:
        """
        Summarizes all registered models and active versions in the registry.
        """
        summary = []
        registered_models = self.client.search_registered_models()
        for rm in registered_models:
            versions = self.client.search_model_versions(f"name='{rm.name}'")
            summary.append({
                "model_name": rm.name,
                "latest_version": versions[0].version if versions else None,
                "production_version": next((v.version for v in versions if v.current_stage == "Production"), None),
                "total_versions": len(versions)
            })
        return summary
