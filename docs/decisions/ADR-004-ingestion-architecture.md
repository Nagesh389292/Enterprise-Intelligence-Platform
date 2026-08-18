# Architecture Decision Record (ADR)

## ADR-004: Selection of a Medallion Data Ingestion Framework with Incremental Checkpoints & Quarantine Isolation

* **Status**: Accepted
* **Date**: 2026-08-17
* **Architect**: Antigravity Engineering Team
* **Deciders**: Enterprise Data Architecture Committee (NexaCore Industries)

---

## 1. Context and Problem Statement

NexaCore Industries produces raw enterprise data across 17 entity domains landing as Parquet and CSV files in `data/raw/generated/`. 

To feed the enterprise PostgreSQL data warehouse, analytics dashboards, feature stores, and predictive ML models, the platform requires a robust data ingestion framework. 

The framework must solve:
1. **Incremental Processing**: Ingesting newly arrived raw files without re-scanning or re-processing previously ingested historical data.
2. **Idempotency**: Ensuring that executing an ingestion job multiple times over identical source files does not generate duplicate records or corrupt metrics.
3. **Data Quality Isolation**: Preventing defective upstream data (null primary keys, invalid dates, negative quantities) from polluting the clean data warehouse while preserving rejected records in quarantine for audit and recovery.
4. **Data Lineage & Traceability**: Guaranteeing that every record in the analytics layer can be traced back to its raw landing file, ingestion batch ID, and pipeline timestamp.

---

## 2. Option Comparison

### Option A: Monolithic Full-Reload Script
* **Pros**: Simple to implement initially.
* **Cons**: Scans and reloads all historical files on every run; scale rapidly degrades as data volume grows; no idempotency or deduplication; bad data crashes the entire load or pollutes database tables silently; lacks audit logging.

### Option B: Medallion Architecture Ingestion Framework (Raw $\rightarrow$ Bronze $\rightarrow$ Silver $\rightarrow$ Gold)
* **Pros**: 
  * **Layered Medallion Boundaries**: Clear separation between immutable raw landing data (Bronze), validated conformed data (Silver), and star-schema analytical models (Gold).
  * **Incremental File Checkpointing**: Uses MD5 file checksums and watermark timestamps stored in `audit.pipeline_execution_logs` to detect new or modified files.
  * **Atomic Idempotent UPSERTs**: Uses deterministic record hashes and PostgreSQL `ON CONFLICT DO UPDATE` semantics to make reprocessing safe.
  * **Quarantine Route**: Defective records are trapped by data contract validation gates and routed to `audit.quarantine_records` without stopping the pipeline.
  * **Full Lineage Metadata**: Every ingested record is tagged with `_ingestion_batch_id`, `_source_file`, and `_ingested_at`.
* **Cons**: Requires explicit architecture design, state checkpointing metadata, and audit logging schemas.

---

## 3. Decision Outcome

**Chosen Option**: **Option B (Medallion Architecture Ingestion Framework)**.

---

## 4. Rationale & Consequences

### Positive Consequences
- **High Operational Reliability**: Pipeline failures leave state checkpoint logs intact, allowing automatic retries from the point of failure.
- **Enterprise Data Observability**: Execution metrics (throughput, rejections, duration) are logged directly to the `audit` schema.
- **Zero Pollution Guarantee**: Database tables in `source` and `analytics` schemas receive strictly validated records.

### Negative Consequences
- Slightly higher disk storage required for Bronze raw archive and quarantine logs.
