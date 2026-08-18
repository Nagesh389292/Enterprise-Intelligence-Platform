# Architecture Decision Record (ADR)

## ADR-001: Selection of Medallion Architecture & Incremental Development Strategy

* **Status**: Accepted
* **Date**: 2026-08-17
* **Architect**: Antigravity Engineering Team
* **Deciders**: Enterprise Data & AI Steering Committee (NexaCore Industries)

---

## 1. Context and Problem Statement

NexaCore Industries operates across multiple business verticals including manufacturing, inventory distribution, retail sales, and customer operations. Historically, data in each vertical has been collected in disparate silos (relational databases, CSV export dumps, REST API endpoints, and IoT telemetry streams).

Management requires a unified intelligence platform capable of delivering business analytics, predictive machine learning models, dynamic forecasting, and operational API endpoints.

Building this system requires answering two core architectural questions:
1. What pattern should govern data storage, cleaning, transformation, and analytical modeling?
2. How should the platform implementation be executed to ensure production-grade software engineering rigor?

---

## 2. Considered Options

### Data Architecture Patterns
* **Option A: Traditional Monolithic ETL directly to Data Warehouse** (Direct ingestion straight into relational database tables).
* **Option B: Medallion Lakehouse Architecture (Bronze → Silver → Gold)** paired with a relational Data Warehouse.

### Implementation Strategies
* **Option X: All-At-Once Monolithic Scripting** (Generate synthetic datasets, train models, and write API scripts simultaneously in single files).
* **Option Y: Incremental Stage-Based Engineering Lifecycle** (Freeze architecture -> Design schema -> Build generator -> Implement PySpark ETL -> Construct dbt models -> Train ML models -> Expose FastAPI serving).

---

## 3. Decision Outcome

**Chosen Option**: **Option B (Medallion Architecture)** combined with **Option Y (Incremental Stage-Based Engineering)**.

---

## 4. Rationale & Justification

### 4.1 Why Medallion Architecture?
1. **Raw Immutability (Bronze Layer)**: Preserves original un-mutated source files, enabling full re-processing and auditability without re-fetching from source systems.
2. **Quality Quarantine & Cleanliness (Silver Layer)**: Decouples raw ingestion from business logic. Bad data can be quarantined and audited without crashing downstream models or dashboards.
3. **Dimensional Star Schemas (Gold Layer)**: Provides high-performance, business-ready star schema dimensional models (`dim_*` and `fact_*`) optimized for complex BI queries and ML feature engineering.

### 4.2 Why Incremental Stage-Based Development?
1. **Production-Grade Rigor**: Prevents architectural technical debt by enforcing proper database schema design, indexing, constraints, and data contracts before writing code.
2. **Deterministic Troubleshooting**: Isolates bugs to specific stages (e.g., distinguishing between an ingestion bug vs a dbt transformation bug vs an ML feature mismatch).
3. **Realistic Enterprise Workflow**: Mirrors high-performing enterprise data engineering and data science team practices.

---

## 5. Consequences & Trade-offs

### Positive Consequences
* Clear separation of responsibilities between Data Engineers, Analytics Engineers, Data Scientists, and ML Engineers.
* Full lineage tracking from raw landing data to API prediction output.
* Strict validation contracts prevent corrupted data from entering training pipelines.

### Negative / Trade-off Consequences
* Higher initial setup complexity compared to a basic monolithic script.
* Storage duplication across Bronze, Silver, and Gold storage tiers.
