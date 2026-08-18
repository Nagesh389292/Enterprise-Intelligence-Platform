"""
CLI Execution Script: MLflow Model Registration & Stage Promotion
==================================================================
Registers trained champion models from 8A-8D MLflow experiments into the central
MLflow Model Registry and promotes them to 'Production' stage.
"""

import sys
import os
import logging

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.mlops.registry import ModelRegistryManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing MLflow Model Registration & Promotion...")
    manager = ModelRegistryManager(tracking_uri="sqlite:///mlflow.db")

    models_to_register = [
        {
            "exp": "Customer_Churn_Prediction",
            "model_name": "Customer_Churn_Classifier",
            "local_path": "models/churn/champion_churn_model.pkl"
        },
        {
            "exp": "Demand_Forecasting_Prediction",
            "model_name": "SKU_Demand_Regressor",
            "local_path": "models/demand/champion_demand_model.pkl"
        },
        {
            "exp": "Inventory_Stockout_Risk_Classification",
            "model_name": "Inventory_Stockout_Classifier",
            "local_path": "models/inventory/champion_stockout_model.pkl"
        },
        {
            "exp": "Machine_Failure_Prediction",
            "model_name": "Machine_Failure_Classifier",
            "local_path": "models/telemetry/champion_failure_model.pkl"
        }
    ]

    registered_count = 0
    for item in models_to_register:
        try:
            reg_info = manager.register_model_from_run(
                experiment_name=item["exp"],
                model_name=item["model_name"],
                local_model_path=item["local_path"]
            )
            manager.promote_model_stage(
                model_name=reg_info["model_name"],
                version=reg_info["version"],
                stage="Production"
            )
            registered_count += 1
            logger.info(f"Registered and promoted '{item['model_name']}' to Production.")
        except Exception as e:
            logger.warning(f"Could not register model for experiment '{item['exp']}': {e}")

    summary = manager.list_all_registered_models()
    logger.info("Current MLflow Registered Models:")
    for rm in summary:
        logger.info(f"  - Model: {rm['model_name']} | Prod Version: v{rm['production_version']} | Total Versions: {rm['total_versions']}")

    print(f"\nModel Registration Completed: {registered_count} models promoted to Production.")

if __name__ == "__main__":
    main()
