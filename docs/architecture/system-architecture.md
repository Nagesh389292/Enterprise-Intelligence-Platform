# System Architecture Specification
### NexaCore Enterprise Data & ML Intelligence Platform (EIP)

---

## 1. Architectural Overview

The **Enterprise Data & ML Intelligence Platform (EIP)** follows a modular **Medallion Data Lakehouse Architecture** integrated with a relational Data Warehouse, MLflow Model Lifecycle Management, and FastAPI REST microservices.

```text
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                           NEXACORE OPERATIONAL DATA SOURCES                     │
  │  [CRM / Customers]  [ERP / Orders & Inventory]  [IoT Telemetry / Machines]      │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                            INGESTION LAYER (Python)                             │
  │  Batch extraction, API connectors, CSV/JSON file ingestion, incremental sync      │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                            BRONZE LAYER (Raw Landing)                           │
  │  Raw, un-mutated landing storage (JSON, CSV, Parquet). Preserves source audit.  │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                    DATA PROCESSING & CLEANING (PySpark / Python)                │
  │  Deduplication, schema enforcement, data quality validation, quarantine routing │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                      SILVER LAYER (Cleaned & Standardized)                      │
  │  Standardized column names, validated types, cleaned metrics, unified keys      │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                    ANALYTICS ENGINEERING (dbt Transformations)                  │
  │  Dimensional modeling (Star Schema), fact/dimension tables, aggregated marts    │
  └───────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                        GOLD LAYER / DATA WAREHOUSE (PostgreSQL)                 │
  │  dim_customers, dim_products, dim_machines, fact_orders, fact_telemetry          │
  └───────────────────┬───────────────────┬───────────────────┬─────────────────────┘
                      │                   │                   │
                      ▼                   ▼                   ▼
           ┌─────────────────────┐ ┌─────────────┐ ┌────────────────────┐
           │ ANALYTICS & BI      │ │ DATA SCIENCE│ │ DATA QUALITY AUDIT │
           │ SQL Reporting /     │ │ ML Training │ │ Great Expectations │
           │ Power BI Dashboards │ │ & MLflow    │ │ Quarantine Monitoring│
           └─────────────────────┘ └──────┬──────┘ └────────────────────┘
                                          │
                                          ▼
                               ┌────────────────────┐
                               │ FASTAPI ML SERVING │
                               │ Real-time Endpoints│
                               └────────────────────┘
```

---

## 2. Layer-by-Layer Architectural Breakdown

### 2.1 Operational Data Sources
* **Customer CRM**: Accounts, contacts, billing tiers, support tickets.
* **ERP System**: Product catalogs, warehouse stock, purchase orders, supplier logs.
* **IoT Industrial Telemetry**: High-frequency sensor streams (temperature, vibration, pressure) from factory equipment.

### 2.2 Ingestion Layer
* **Responsibilities**: Extract incremental records from external APIs, raw file uploads, and operational database snapshots.
* **Technology**: Modular Python extractors with configurable execution schedules.
* **Target Output**: Bronze storage directory (`data/raw/`).

### 2.3 Bronze Layer (Raw Storage Tier)
* **Format**: Raw JSON / CSV files landed into partitioned directory paths by entity and date (`data/raw/<entity>/YYYY/MM/DD/`).
* **Immutability**: Data in Bronze is append-only and never modified to preserve raw source lineage.

### 2.4 Data Processing & Quality Layer
* **Engine**: PySpark for distributed batch execution and schema validation.
* **Validation & Quarantine**: Incoming records undergo data contract checks (non-null primary keys, type assertion, range checks). Records failing validation are routed to a `quarantine` location for auditing.

### 2.5 Silver Layer (Cleansed Tier)
* **Format**: Optimized Parquet / Cleaned tables with standardized schemas, UTC timestamps, and cleansed string encodings.
* **Purpose**: Single source of cleaned truth ready for analytical modeling.

### 2.6 Analytics Engineering & Gold Layer (dbt + PostgreSQL)
* **Engine**: **dbt (Data Build Tool)** executing against PostgreSQL.
* **Modeling Strategy**: Star Schema Dimensional Modeling.
  * **Dimensions**: `dim_customers`, `dim_products`, `dim_warehouses`, `dim_machines`, `dim_date`.
  * **Facts**: `fact_orders`, `fact_inventory_daily`, `fact_telemetry_hourly`, `fact_support_tickets`.
  * **Data Marts**: `mart_sales_monthly`, `mart_customer_churn_features`, `mart_inventory_health`.

### 2.7 Machine Learning Lifecycle & Serving
* **Experimentation & Registry**: Scikit-learn and XGBoost model pipelines trained on Gold data marts. All runs logged into **MLflow** with metrics, parameters, and model artifacts.
* **Serving API**: **FastAPI** application serving real-time inferences for churn risk, demand prediction, and telemetry anomalies.
