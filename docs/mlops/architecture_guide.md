# Enterprise MLOps Platform Architecture & Operational Guide

## Executive Overview

The **Enterprise MLOps & ML Platform (Stage 9)** operationalizes baseline Machine Learning models (Customer Churn, Demand Forecasting, Inventory Stockout Risk, Machine Telemetry Health) into a production-grade infrastructure.

```text
                                  PostgreSQL / Gold
                                        │
                                        ▼
                            Feature Extraction & Pipeline
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
            Churn (8A)             Demand (8B)           Stockout (8C) & Telemetry (8D)
                 │                      │                      │
                 └──────────────────────┼──────────────────────┘
                                        ▼
                           MLflow Model Registry
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                Batch Inference Engine          FastAPI REST Microservice
                         │                             │
                         ▼                             ▼
              PostgreSQL Prediction Store       Live Inference API (/predict/*)
               (analytics.fact_predictions_*)          │
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                       Data & Prediction Drift Monitor
                               (docs/mlops/drift_report.json)
```

---

## Key System Components

### 1. MLflow Model Registry (`data_science/mlops/registry.py`)
- **Central Storage:** `sqlite:///mlflow.db`
- **Stage Lifecycle:** `None → Staging → Production → Archived`
- **Aliases:** `@production`, `@staging`
- **Programmatic Promotion:** `ModelRegistryManager.promote_model_stage()` promotes top out-of-fold benchmark champions while auto-archiving legacy versions.

### 2. Production Batch Inference Engine (`data_science/mlops/batch_inference.py`)
- Executes scheduled batch inference over PostgreSQL Gold feature tables.
- Writes structured prediction records to four dedicated fact tables in `analytics`:
  - `analytics.fact_predictions_customer_churn`
  - `analytics.fact_predictions_sku_demand`
  - `analytics.fact_predictions_inventory_stockout`
  - `analytics.fact_predictions_machine_health`

### 3. Statistical Drift & Monitoring Pipeline (`data_science/mlops/drift_detector.py`)
- Evaluates feature distribution shifts and prediction drift between baseline training datasets and current scoring batches.
- **Metrics:** Kolmogorov-Smirnov (KS-test p-value $< 0.01$) and Population Stability Index ($\text{PSI} \ge 0.25$).
- **Export:** `docs/mlops/drift_report.json` with automated retraining recommendations.

### 4. FastAPI Model Serving REST Microservice (`data_science/mlops/serving_api.py`)
- Enterprise REST microservice providing online real-time inference with Pydantic v2 schemas.
- **Endpoints:**
  - `GET /health`: Microservice health check & registered manifest.
  - `POST /predict/churn`: Online churn probability & risk tier (`Low`, `Medium`, `High`).
  - `POST /predict/demand`: Online daily SKU demand forecast & 95% confidence interval bounds.
  - `POST /predict/stockout`: Online 7-day inventory stockout probability & severity (`Low`, `Moderate`, `Critical`).
  - `POST /predict/machine-health`: Online telemetry anomaly score & 24h failure probability.

---

## Operational Commands

### Register & Promote Models to Production
```bash
python scripts/register_and_promote_models.py
```

### Run Batch Inference & Populate Prediction Tables
```bash
python scripts/run_batch_inference.py
```

### Run Data & Prediction Drift Audit
```bash
python scripts/run_drift_monitoring.py
```

### Run Full Stage 9 Master Pipeline
```bash
python scripts/run_stage9_mlops.py
```

### Start FastAPI Model Serving Microservice Locally
```bash
uvicorn data_science.mlops.serving_api:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at `http://localhost:8000/docs`.
