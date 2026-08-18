# Architecture Decision Record (ADR)

## ADR-002: Selection of a Deterministic Enterprise Data Generation Engine vs. Static Public Datasets

* **Status**: Accepted
* **Date**: 2026-08-17
* **Architect**: Antigravity Engineering Team
* **Deciders**: Enterprise Data & AI Steering Committee (NexaCore Industries)

---

## 1. Context and Problem Statement

To validate our enterprise data platform across data engineering, analytics engineering, data science, and ML engineering, the platform requires multi-domain enterprise data spanning customers, products, sales transactions, warehouses, inventory, industrial IoT telemetry, maintenance events, and customer support tickets.

The platform must demonstrate capabilities in:
1. Handling complex relational integrity and multi-table parent-child relationships.
2. Ingesting and validating data with controlled, realistic data quality defects.
3. Training ML models on realistic causal business signals (churn, demand forecasting, equipment anomaly detection).
4. Benchmarking distributed ETL pipeline performance under scaling data volumes (10K to 20M+ records).

We must decide whether to use static public datasets (e.g., Kaggle, UCI ML repository) or build a custom **Deterministic Enterprise Data Generation Engine**.

---

## 2. Option Comparison

### Option A: Use Static Public Datasets (e.g., Kaggle retail/telemetry CSVs)
* **Pros**: Pre-packaged, no generator code required.
* **Cons**: Fragmented schemas across unrelated sources; lacks cross-domain relational integrity (e.g., Kaggle retail data has no link to industrial IoT telemetry or support tickets); clean static datasets lack controlled data quality defects; fixed scale cannot be dynamically expanded for performance benchmarking.

### Option B: Deterministic Enterprise Data Generation Engine (`enterprise_data_generator`)
* **Pros**: 
  * **Unified Multi-Domain Relational Graph**: Customer purchases directly drive inventory depletion, support tickets, and churn risk.
  * **Configurable Scale Profiles**: Seamlessly scales from lightweight `development` sets (10K orders) to `scale` benchmarks (2M orders / 20M IoT signals).
  * **Injected Causal ML Signals**: Introduces realistic business patterns (e.g., machine temperature degradation prior to failure) without target leakage.
  * **Controlled Data Quality Corruption**: Enables testing data quality pipelines by injecting configurable bad data (orphaned keys, nulls, negative quantities, schema drift).
  * **Deterministic Reproducibility**: Using seed-based random number generation guarantees identical output across developer environments.
* **Cons**: Requires initial architectural design and software module development.

---

## 3. Decision Outcome

**Chosen Option**: **Option B (Deterministic Enterprise Data Generation Engine)**.

---

## 4. Rationale & Consequences

By building a dedicated generation engine, NexaCore Industries gains complete control over data volume, relational integrity, temporal trends, ML signal strength, and data quality degradation.

### Positive Consequences
- **True End-to-End Alignment**: Cross-domain queries can join customer support tickets with product SKUs and machine telemetry.
- **Data Quality Pipeline Testing**: Quarantine logic can be battle-tested against reproducible corruption scenarios.
- **Scalability Benchmarking**: Pipelines can be stress-tested across different scale profiles (`dev`, `integration`, `scale`).

### Negative Consequences
- Generator codebase requires maintenance and validation testing.
