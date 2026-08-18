"""
Integration Test Suite: Stage 9 Enterprise MLOps & ML Platform
================================================================
Validates MLflow Model Registry, Batch Inference Engine, PostgreSQL Prediction Store,
Drift Monitoring Engine, and FastAPI Model Serving REST endpoints.
"""

import sys
import os
import json
import pytest
import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.db import get_engine, read_sql
from data_science.mlops.registry import ModelRegistryManager
from data_science.mlops.batch_inference import BatchInferenceEngine
from data_science.mlops.drift_detector import DriftDetector
from data_science.mlops.serving_api import app

client = TestClient(app)

def test_model_registry_initialization():
    """Verify ModelRegistryManager interacts cleanly with MLflow database."""
    manager = ModelRegistryManager(tracking_uri="sqlite:///mlflow.db")
    models = manager.list_all_registered_models()
    assert isinstance(models, list)

def test_batch_inference_execution():
    """Verify BatchInferenceEngine executes batch predictions across all 4 domains."""
    engine = get_engine()
    batch = BatchInferenceEngine(db_engine=engine)
    results = batch.run_all_batch_inferences()

    assert "churn" in results
    assert "demand" in results
    assert "stockout" in results
    assert "machine_health" in results

def test_prediction_tables_populated():
    """Verify PostgreSQL analytics prediction tables contain structured output records."""
    engine = get_engine()
    df_churn = read_sql("SELECT COUNT(*) as cnt FROM analytics.fact_predictions_customer_churn;", engine)
    df_demand = read_sql("SELECT COUNT(*) as cnt FROM analytics.fact_predictions_sku_demand;", engine)
    df_stockout = read_sql("SELECT COUNT(*) as cnt FROM analytics.fact_predictions_inventory_stockout;", engine)
    df_health = read_sql("SELECT COUNT(*) as cnt FROM analytics.fact_predictions_machine_health;", engine)

    assert df_churn.iloc[0]["cnt"] > 0
    assert df_demand.iloc[0]["cnt"] > 0
    assert df_stockout.iloc[0]["cnt"] > 0
    assert df_health.iloc[0]["cnt"] > 0

def test_drift_monitoring_audit():
    """Verify DriftDetector generates structured JSON drift report."""
    detector = DriftDetector()
    results = detector.run_drift_audit()

    assert "domains" in results
    assert os.path.exists("docs/mlops/drift_report.json")

def test_fastapi_health_endpoint():
    """Verify FastAPI /health endpoint returns 200 OK and active model manifest."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "customer_churn" in data["active_models"]

def test_fastapi_predict_churn():
    """Verify FastAPI /predict/churn online prediction endpoint."""
    payload = {
        "customer_id": "TEST_CUST_101",
        "tenure_months": 14.5,
        "total_orders": 8,
        "total_spend": 750.0,
        "avg_order_value": 93.75,
        "avg_csat_score": 4.2,
        "days_since_last_order": 18.0
    }
    response = client.post("/predict/churn", json=payload, headers={"X-API-Key": "nexacore_prod_secret_api_key_2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "TEST_CUST_101"
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_tier"] in ["Low", "Medium", "High"]

def test_fastapi_predict_demand():
    """Verify FastAPI /predict/demand online prediction endpoint."""
    payload = {
        "product_id": "TEST_PROD_202",
        "unit_price": 45.00,
        "lag_1_demand": 15.0,
        "lag_7_demand": 14.0,
        "rolling_avg_7d": 14.5,
        "rolling_std_7d": 1.2,
        "day_of_week": 3,
        "is_weekend": 0
    }
    response = client.post("/predict/demand", json=payload, headers={"X-API-Key": "nexacore_prod_secret_api_key_2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "TEST_PROD_202"
    assert data["predicted_demand_units"] >= 0.0

def test_fastapi_predict_stockout():
    """Verify FastAPI /predict/stockout online prediction endpoint."""
    payload = {
        "item_id": "TEST_ITEM_303",
        "warehouse_id": "WH-1",
        "category": "Electronics",
        "lead_time_days": 4.0,
        "avg_daily_consumption": 12.0,
        "pending_reorder_units": 0.0,
        "supplier_reliability_score": 0.92
    }
    response = client.post("/predict/stockout", json=payload, headers={"X-API-Key": "nexacore_prod_secret_api_key_2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "TEST_ITEM_303"
    assert 0.0 <= data["stockout_risk_prob_7d"] <= 1.0

def test_fastapi_predict_machine_health():
    """Verify FastAPI /predict/machine-health online prediction endpoint."""
    payload = {
        "machine_id": "TEST_MACH_404",
        "temperature_celsius": 88.5,
        "vibration_mm_s": 4.8,
        "pressure_psi": 115.0,
        "rotational_speed_rpm": 2100.0,
        "temp_roll6_mean": 86.0,
        "vib_roll6_mean": 4.5,
        "temp_roll6_std": 2.1,
        "vib_roll6_std": 0.8
    }
    response = client.post("/predict/machine-health", json=payload, headers={"X-API-Key": "nexacore_prod_secret_api_key_2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["machine_id"] == "TEST_MACH_404"
    assert data["health_status"] in ["Normal", "Warning", "Critical"]

