-- ==============================================================================
-- Enterprise Intelligence Platform — Database Initialization Script 04
-- Description: Creates Pipeline Execution, Data Quality & Quarantine Audit Tables under 'audit' schema
-- ==============================================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_execution_logs (
    execution_id BIGSERIAL PRIMARY KEY,
    etl_batch_id VARCHAR(50) NOT NULL,
    pipeline_name VARCHAR(100) NOT NULL,
    source_layer VARCHAR(30) NOT NULL CHECK (source_layer IN ('BRONZE','SILVER','GOLD')),
    target_table VARCHAR(100) NOT NULL,
    records_ingested INT NOT NULL DEFAULT 0 CHECK (records_ingested >= 0),
    records_rejected INT NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('RUNNING','SUCCESS','FAILED','WARNING')),
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit.data_quality_audit_logs (
    audit_id BIGSERIAL PRIMARY KEY,
    etl_batch_id VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- e.g., NULL_CHECK, TYPE_CHECK, UNIQUE_CHECK, RANGE_CHECK
    records_tested INT NOT NULL DEFAULT 0,
    records_failed INT NOT NULL DEFAULT 0,
    assertion_status VARCHAR(20) NOT NULL CHECK (assertion_status IN ('PASSED','FAILED')),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit.quarantine_records (
    quarantine_id BIGSERIAL PRIMARY KEY,
    etl_batch_id VARCHAR(50) NOT NULL,
    source_table VARCHAR(100) NOT NULL,
    quarantine_reason VARCHAR(255) NOT NULL,
    raw_record_json JSONB NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
