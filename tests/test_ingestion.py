# ==============================================================================
# Enterprise Intelligence Platform — Ingestion Framework Test Suite
# Tests SHA-256 discovery, live PostgreSQL Silver loading, Run 1 vs Run 2 idempotency,
# quarantine dead-letter routing, and failed batch retry history.
# ==============================================================================

import os
import uuid
import tempfile
import pandas as pd
import pytest
from sqlalchemy import text
from scripts.ingestion.discovery import FileDiscoveryEngine
from scripts.ingestion.checkpoint import CheckpointStore
from scripts.ingestion.postgres import get_engine
from scripts.ingestion.cli import run_ingested_batch
from scripts.ingestion.quarantine import QuarantineWriter
from scripts.ingestion.audit import AuditLogger

@pytest.fixture(scope="module")
def db_engine():
    engine = get_engine()
    # Clean test tables for reproducible test suite execution
    tables = [
        "customer_satisfaction", "ticket_interactions", "support_tickets",
        "failure_events", "maintenance_events", "machine_telemetry", "machines", "machine_types",
        "inventory_transactions", "inventory", "warehouses", "suppliers",
        "order_items", "orders", "products", "product_categories", "sales_channels",
        "customer_interactions", "customer_addresses", "customers", "customer_segments"
    ]
    with engine.begin() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE source.{t} CASCADE;"))
        conn.execute(text("TRUNCATE TABLE audit.pipeline_execution_logs CASCADE;"))
        conn.execute(text("TRUNCATE TABLE audit.data_quality_audit_logs CASCADE;"))
        conn.execute(text("TRUNCATE TABLE audit.quarantine_records CASCADE;"))
        conn.execute(text("""
            INSERT INTO source.sales_channels (channel_id, channel_code, channel_name, commission_rate) VALUES
            (1, 'DIRECT', 'Direct Enterprise Sales', 0.0500),
            (2, 'PARTNER', 'Partner Channel Network', 0.1000),
            (3, 'ONLINE', 'Digital Self-Service Portal', 0.0200)
            ON CONFLICT (channel_id) DO NOTHING;
        """))
    return engine


def test_sha256_file_discovery():
    """Verifies that discovery engine scans files and computes 64-character SHA-256 hashes."""
    engine = FileDiscoveryEngine()
    files = engine.discover_files("data/raw/generated", "parquet")
    
    assert len(files) > 0
    for f in files:
        assert len(f["file_checksum"]) == 64
        assert f["file_name"].endswith(".parquet")

def test_first_run_ingestion(db_engine):
    """Verifies first-run batch ingestion loads records into source.* PostgreSQL tables."""
    res = run_ingested_batch(input_dir="data/raw/generated", file_format="parquet")
    
    assert res["processed"] > 0
    assert res["skipped"] == 0
    
    # Query database counts for customers and orders
    with db_engine.connect() as conn:
        cust_cnt = conn.execute(text("SELECT COUNT(*) FROM source.customers;")).scalar()
        ord_cnt = conn.execute(text("SELECT COUNT(*) FROM source.orders;")).scalar()
        
    assert cust_cnt == 1000
    assert ord_cnt == 10000

def test_second_run_idempotency(db_engine):
    """MANDATORY IDEMPOTENCY TEST: Re-running ingestion over identical files skips 100% of rows."""
    # Second run over identical raw files
    res2 = run_ingested_batch(input_dir="data/raw/generated", file_format="parquet")
    
    assert res2["processed"] == 0
    assert res2["skipped"] == 17
    
    # Assert database counts remain identical (0 duplicates added)
    with db_engine.connect() as conn:
        cust_cnt = conn.execute(text("SELECT COUNT(*) FROM source.customers;")).scalar()
        ord_cnt = conn.execute(text("SELECT COUNT(*) FROM source.orders;")).scalar()
        
    assert cust_cnt == 1000
    assert ord_cnt == 10000

def test_quarantine_dead_letter(db_engine):
    """Verifies defective records are trapped in audit.quarantine_records and not loaded to Silver."""
    quarantine_writer = QuarantineWriter()
    test_batch_id = f"batch_test_{uuid.uuid4().hex[:6]}"
    
    bad_records = [
        {"row_dict": {"order_number": None, "total_amount": 100.0}, "failed_rule": "NON_NULL_ORDER_NUMBER"},
        {"row_dict": {"order_number": "ORD-BAD-01", "total_amount": -50.0}, "failed_rule": "POSITIVE_TOTAL_AMOUNT"}
    ]
    
    q_count = quarantine_writer.write_quarantine(test_batch_id, "test_orders.parquet", "orders", bad_records)
    assert q_count == 2
    
    with db_engine.connect() as conn:
        q_db_cnt = conn.execute(text("SELECT COUNT(*) FROM audit.quarantine_records WHERE batch_id = :b;"), {"b": test_batch_id}).scalar()
    assert q_db_cnt == 2

def test_failed_batch_retry_history(db_engine):
    """Verifies failed execution logs are preserved and retry creates a new attempt log."""
    audit_logger = AuditLogger()
    checkpoint = CheckpointStore()
    
    test_file = f"test_retry_{uuid.uuid4().hex[:6]}.parquet"
    test_hash = uuid.uuid4().hex + uuid.uuid4().hex
    
    # Attempt 1: Failed
    batch_1 = f"batch_fail_{uuid.uuid4().hex[:6]}"
    log_1 = audit_logger.start_file_log(batch_1, "test_pipe", test_file, test_hash, 1024, 100)
    audit_logger.fail_file_log(log_1, "Simulated network failure during write")
    
    # Verify Attempt 1 history preserved in database
    history_1 = checkpoint.get_latest_execution_history(test_file)
    assert len(history_1) == 1
    assert history_1[0]["status"] == "FAILED"
    assert history_1[0]["batch_id"] == batch_1
    
    # Attempt 2: Successful Retry
    batch_2 = f"batch_success_{uuid.uuid4().hex[:6]}"
    log_2 = audit_logger.start_file_log(batch_2, "test_pipe", test_file, test_hash, 1024, 100)
    audit_logger.complete_file_log(log_2, records_processed=100, records_quarantined=0)
    
    # Verify BOTH Attempt 1 and Attempt 2 exist in audit history
    history_2 = checkpoint.get_latest_execution_history(test_file)
    assert len(history_2) == 2
    assert history_2[0]["status"] == "COMPLETED"
    assert history_2[0]["batch_id"] == batch_2
    assert history_2[1]["status"] == "FAILED"
    assert history_2[1]["batch_id"] == batch_1
