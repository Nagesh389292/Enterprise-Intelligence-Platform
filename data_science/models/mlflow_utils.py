"""
data_science/models/mlflow_utils.py
----------------------------------
MLflow tracking helper for logging experiments, parameters, metrics,
evaluation figures, and model artifacts locally to `sqlite:///mlflow.db`.
"""

import os
import json
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.lightgbm

os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"


class MLflowTracker:
    def __init__(self, experiment_name: str = "Customer_Churn_Prediction", tracking_uri: str = "sqlite:///mlflow.db"):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)

    def log_run(
        self,
        run_name: str,
        params: dict,
        metrics: dict,
        figures: dict = None,
        artifacts: dict = None,
        model=None,
        model_type: str = "sklearn"
    ) -> str:
        """
        Log a complete training run to MLflow.
        Returns the run_id.
        """
        with mlflow.start_run(run_name=run_name) as run:
            run_id = run.info.run_id

            # 1. Log hyperparameters
            for k, v in params.items():
                mlflow.log_param(k, str(v))

            # 2. Log metrics
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, float(v))

            # 3. Log figures (matplotlib figures saved as artifacts)
            if figures:
                os.makedirs("scratch/mlflow_figures", exist_ok=True)
                for fig_name, fig in figures.items():
                    filepath = f"scratch/mlflow_figures/{fig_name}.png"
                    fig.savefig(filepath, bbox_inches="tight", dpi=150)
                    mlflow.log_artifact(filepath, artifact_path="plots")
                    plt.close(fig)

            # 4. Log dictionary artifacts (e.g. JSON reports, feature importances)
            if artifacts:
                os.makedirs("scratch/mlflow_artifacts", exist_ok=True)
                for art_name, art_data in artifacts.items():
                    filepath = f"scratch/mlflow_artifacts/{art_name}.json"
                    with open(filepath, "w") as f:
                        json.dump(art_data, f, indent=2, default=str)
                    mlflow.log_artifact(filepath, artifact_path="metadata")

            # 5. Log model artifact
            if model is not None:
                if model_type == "xgboost":
                    mlflow.xgboost.log_model(model, artifact_path="model")
                elif model_type == "lightgbm":
                    mlflow.lightgbm.log_model(model, artifact_path="model")
                else:
                    mlflow.sklearn.log_model(model, artifact_path="model")

            return run_id
