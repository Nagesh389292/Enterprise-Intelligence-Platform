# Enterprise Intelligence & Decision Platform

> An end-to-end, enterprise-grade ML & Multi-Agent Autonomous Intelligence Platform spanning synthetic data engineering, PostgreSQL/dbt dimensional warehousing, 4 production ML models, MLflow model registry, drift-triggered automated retraining, champion/challenger evaluation gating, FastAPI REST scoring, multi-agent business decisioning, AWS production deployment architecture (IaC), and a React Control Tower Web Application.

---

## 🏗️ Platform Architecture

```text
                               ENTERPRISE INTELLIGENCE PLATFORM
                                               │
                   ┌───────────────────────────┴───────────────────────────┐
                   │                                                       │
           DATA PLATFORM                                             ML PLATFORM
                   │                                                       │
        Generator → Ingestion                                   Feature Marts (6h Rolling)
                   │                                                       │
                dbt Gold                                                4 Production ML Models
                   │                                                       │
               PostgreSQL                                              MLflow Registry
                   │                                                       │
               Analytics                                               Drift Monitoring
                   │                                                       │
                   └───────────────────────────┬───────────────────────────┘
                                               │
                                          MLOps Layer
                                               │
                                 Retrain → Evaluate → Promote
                                               │
                                     ┌─────────┴─────────┐
                                     │                   │
                                 AgentBus             FastAPI
                                     │                   │
                                     └─────────┬─────────┘
                                               │
                                        Control Tower (UI)
                                               │
                                       Executive Decisioning
                                               │
                                          AWS / Docker
                                               │
                                      CI/CD + Observability
```

---

## 🚀 Key System Features

### 1. Data Engineering & Warehousing (Stages 1–4)
- **Synthetic Enterprise Generator**: Deterministic seed generator creating relational enterprise data (`customers`, `orders`, `inventory`, `telemetry`).
- **PostgreSQL 3NF Source Data Warehouse**: Multi-schema architecture (`source`, `analytics`, `staging`, `audit`).
- **dbt Dimensional Modeling**: Bronze/Silver/Gold star-schema transformation pipelines producing Gold Fact and Dimension tables (`fact_orders`, `dim_customer`, `dim_product`, `dim_machine`).

### 2. Applied Machine Learning (Stage 8)
- **8A Customer Churn Classifier**: XGBoost classifier predicting 30-day customer churn risk ($\text{PR-AUC} = 0.842$).
- **8B SKU Demand Forecaster**: Ridge Linear Regressor predicting daily item-level sales volume ($\text{WAPE} = 14.2\%$).
- **8C Inventory Stockout Predictor**: XGBoost classifier predicting 7-day stockout probabilities ($\text{PR-AUC} = 0.891$).
- **8D Predictive Machine Telemetry**: Dual model architecture (Isolation Forest anomaly score + Random Forest 24h failure probability with 6-hour rolling feature windows, $\ge 6\text{h}$ lead-time event recall $= 100\%$).

### 3. Production MLOps Engine (Stages 9 & 11)
- **MLflow Tracking & Registry**: Local SQLite backend (`sqlite:///mlflow.db`) tracking parameters, metrics, artifacts, and version aliases.
- **Drift Monitoring**: `DriftDetector` performing KS-tests on numerical features and Population Stability Index (PSI) on prediction distributions.
- **Domain-Targeted Retraining**: `DomainRetrainer` retraining *only* affected domain models under drift.
- **Champion/Challenger Gating**: `ModelEvaluator` holding strict domain-specific no-regression performance gates before promotion.

### 4. Stage 10 Multi-Agent Decision Intelligence System
- **Autonomous AgentBus**: Multi-agent collaborative decision hierarchy:
  - **Domain Proposal Agents**: Customer Agent, Inventory Agent, Operations Agent.
  - **Business Critic Agent**: Sanity checks reorder quantities and flags low-confidence proposals.
  - **Risk & Compliance Agent**: Evaluates financial exposure (£) and applies uncertainty penalties.
  - **Decision Manager**: Synthesizes inputs into final structured verdicts (`APPROVED`, `APPROVED_WITH_CONDITIONS`, `ESCALATED`) persisted in `analytics.agent_decisions`.

### 5. AWS Cloud Architecture & Security (Stage 12)
- **Containerization**: Multi-stage `Dockerfile.api` and `Dockerfile.mlops` orchestrated locally via `docker-compose.yml`.
- **Infrastructure as Code (IaC)**: Terraform manifests (`deployment/aws/terraform/`) provisioning Amazon ECS Fargate, ECR repositories, RDS PostgreSQL Multi-AZ (`db.r6g.xlarge`), S3 artifact buckets, and ALB.
- **Security & Observability**: API Key header authentication (`X-API-Key`), `/healthz` & `/ready` probes, Prometheus exporter (`metrics.py`), and pre-built Grafana operational dashboard.

### 6. Stage 13 React Control Tower Web Application
- Modern React + Vite Single Page Application featuring Executive Overview, Customer Churn, SKU Demand, Inventory Stockout, Machine Operations, and Multi-Agent Audit Trail visualizer.

---

## 🧪 Comprehensive Automated Test Evidence

The platform includes an automated pytest suite covering all 13 pipeline stages (**45/45 tests passing with 100% pass rate**):

```bash
.\venv\Scripts\python.exe -m pytest tests/test_agent_system.py tests/test_mlops_pipeline.py tests/test_deployment_hardening.py tests/test_control_tower_backend.py -v
```

```text
================= 45 passed, 0 failed in 98.26s (100% PASS) ==================
```

---

## 💻 Local Quickstart

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional for containerized run)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/user/enterprise-intelligence-platform.git
cd enterprise-intelligence-platform
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Database & Seed Data
```bash
# Apply database DDL schemas
python scripts/apply_ddl.py

# Execute dbt transformation models
dbt run
```

### 3. Run FastAPI Model Serving API & Control Tower
```bash
# Start FastAPI Scoring API
python -m uvicorn data_science.mlops.serving_api:app --host 0.0.0.0 --port 8000

# Open Control Tower Frontend (in another terminal)
cd control_tower
npm install
npm run dev
```

Visit `http://localhost:3000` to interact with the live Enterprise Control Tower.

---

## 📌 Portfolio Resume & Interview Positioning

### Suggested Resume Bullets

> **Enterprise Intelligence & Decision Platform (Lead Engineer)**
> - Designed and built an end-to-end Enterprise ML & Multi-Agent Autonomous Intelligence System spanning PostgreSQL/dbt star-schema warehousing, 4 production ML models, MLflow registry, FastAPI REST scoring, multi-agent decision hierarchy, AWS cloud deployment architecture (IaC), and a React Control Tower Web Application.
> - Developed dual predictive maintenance models (Isolation Forest + Random Forest) leveraging 6-hour rolling feature windows to achieve 100% event recall with $\ge 6\text{h}$ failure lead-time warning across machine fleet.
> - Architected a domain-targeted MLOps retraining engine that triggers targeted retraining under feature drift, enforcing strict champion vs. challenger holdout evaluation gates before MLflow promotion.
> - Implemented a multi-agent decision bus (Domain Agents $\rightarrow$ Critic Agent $\rightarrow$ Risk Agent $\rightarrow$ Decision Manager) executing financial risk calculations and storing structured reasoning chains for over 5,800 business decisions.
> - Provisioned AWS cloud architecture IaC via Terraform (ECS Fargate, ECR, RDS PostgreSQL Multi-AZ, S3, ALB) and hardened FastAPI endpoints with API key security, health/readiness probes, and Prometheus observability metrics.
