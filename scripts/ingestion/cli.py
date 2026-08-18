"""
NexaCore Data Ingestion Framework CLI Entrypoint.
Orchestrates file discovery, SHA-256 checkpointing, Bronze archiving, contract validation,
quarantine isolation, Silver PostgreSQL UPSERT loading, and audit observability logging.
"""

import os
import sys
import time
import uuid
import argparse
import pandas as pd
from datetime import datetime
from typing import Dict, List
from sqlalchemy import text

from .discovery import FileDiscoveryEngine
from .checkpoint import CheckpointStore
from .bronze import BronzeWriter
from .validation import QualityValidator
from .quarantine import QuarantineWriter
from .silver import SilverLoader
from .audit import AuditLogger

PIPELINE_NAME = "nexacore_batch_ingestion"

# Topological Dependency Order for Relational Ingestion
INGESTION_TOPOLOGICAL_ORDER = [
    # Tier 1: Reference Lookup Tables
    "customer_segments",
    "product_categories",
    "sales_channels",
    "machine_types",
    "suppliers",
    "warehouses",
    
    # Tier 2: Core Entities
    "customers",
    "products",
    "machines",
    
    # Tier 3: Transactional & Event Entities
    "customer_addresses",
    "orders",
    "order_items",
    "inventory",
    "machine_telemetry",
    "maintenance_events",
    "failure_events",
    "support_tickets",
    "customer_satisfaction"
]

def sort_by_topological_order(discovered_files: List[Dict]) -> List[Dict]:
    order_map = {name: idx for idx, name in enumerate(INGESTION_TOPOLOGICAL_ORDER)}
    return sorted(discovered_files, key=lambda f: order_map.get(f["entity_name"], 999))

def run_discovery(input_dir: str = "data/raw/generated", file_format: str = "parquet"):
    engine = FileDiscoveryEngine()
    checkpoint = CheckpointStore()
    
    discovered = engine.discover_files(input_dir, file_format)
    discovered = sort_by_topological_order(discovered)
    
    print("==================================================")
    print("NexaCore Ingestion File Discovery")
    print("==================================================")
    print(f"Landing Directory: {input_dir}")
    print(f"Total Discovered Files: {len(discovered)}")
    print("--------------------------------------------------")
    
    new_files = 0
    skipped_files = 0
    for f in discovered:
        is_done = checkpoint.is_file_processed(f["file_name"], f["file_checksum"])
        status_str = "ALREADY_PROCESSED (SKIP)" if is_done else "NEW_FILE (TO_PROCESS)"
        print(f"  {f['entity_name']:<25}: SHA256={f['file_checksum'][:12]}... | {status_str}")
        if is_done:
            skipped_files += 1
        else:
            new_files += 1
            
    print("--------------------------------------------------")
    print(f"Summary: {new_files} files queued for ingestion | {skipped_files} files skipped")
    print("==================================================")
    return discovered

def run_ingested_batch(
    input_dir: str = "data/raw/generated",
    file_format: str = "parquet",
    force: bool = False
) -> dict:
    discovery_engine = FileDiscoveryEngine()
    checkpoint_store = CheckpointStore()
    bronze_writer = BronzeWriter()
    validator = QualityValidator()
    quarantine_writer = QuarantineWriter()
    silver_loader = SilverLoader()
    audit_logger = AuditLogger()
    
    discovered_files = discovery_engine.discover_files(input_dir, file_format)
    discovered_files = sort_by_topological_order(discovered_files)
    
    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_short_id = uuid.uuid4().hex[:6]
    batch_id = f"batch_{batch_timestamp}_{batch_short_id}"
    
    print("==================================================")
    print("NexaCore Medallion Ingestion Execution")
    print("==================================================")
    print(f"Batch Execution ID: {batch_id}")
    print(f"Source Directory:   {input_dir}")
    print(f"Target Database:    PostgreSQL source.* (Silver)")
    print("--------------------------------------------------")
    
    results = {}
    total_processed = 0
    total_quarantined = 0
    total_skipped = 0
    
    t0 = time.time()
    
    for file_meta in discovered_files:
        file_name = file_meta["file_name"]
        file_path = file_meta["file_path"]
        checksum = file_meta["file_checksum"]
        entity_name = file_meta["entity_name"]
        size_bytes = file_meta["file_size_bytes"]
        
        # Check idempotency checkpoint unless force replay
        if not force and checkpoint_store.is_file_processed(file_name, checksum):
            print(f"  [SKIP] {entity_name:<25}: Previously ingested (SHA256={checksum[:8]}...)")
            total_skipped += 1
            continue
            
        print(f"  [INGESTING] {entity_name:<21} ...", end="", flush=True)
        
        # Read raw Parquet file
        df = pd.read_parquet(file_path)
        records_discovered = len(df)
        
        # 1. Log start in audit database
        log_id = audit_logger.start_file_log(
            batch_id=batch_id,
            pipeline_name=PIPELINE_NAME,
            source_file_name=file_name,
            file_checksum=checksum,
            file_size_bytes=size_bytes,
            records_discovered=records_discovered
        )
        
        try:
            # 2. Archive copy in Bronze immutable store
            bronze_path = bronze_writer.archive_raw_file(file_path, batch_id)
            
            # 3. Validation Gate
            valid_df, invalid_records = validator.validate_entity(entity_name, df)
            
            # 4. Route invalid rows to Quarantine
            n_quarantined = 0
            if invalid_records:
                n_quarantined = quarantine_writer.write_quarantine(
                    batch_id=batch_id,
                    source_file=file_name,
                    entity_name=entity_name,
                    invalid_records=invalid_records
                )
                audit_logger.log_quality_assertion(
                    batch_id=batch_id,
                    table_name=entity_name,
                    rule_name="CONTRACT_VALIDATION",
                    evaluated=records_discovered,
                    passed=len(valid_df),
                    failed=n_quarantined
                )
                
            # 5. Load valid rows into Silver (source.*) using grain-aware UPSERT
            n_inserted = silver_loader.load_entity(
                entity_name=entity_name,
                df=valid_df,
                batch_id=batch_id,
                source_file=file_name,
                source_checksum=checksum
            )
            
            # 6. Complete audit log record
            audit_logger.complete_file_log(log_id, records_processed=n_inserted, records_quarantined=n_quarantined)
            
            total_processed += n_inserted
            total_quarantined += n_quarantined
            results[entity_name] = {"processed": n_inserted, "quarantined": n_quarantined, "status": "COMPLETED"}
            
            print(f" OK! ({n_inserted:,} inserted | {n_quarantined} quarantined)")
            
        except Exception as e:
            audit_logger.fail_file_log(log_id, error_message=str(e))
            print(f" FAILED! ({e})")
            results[entity_name] = {"processed": 0, "quarantined": 0, "status": "FAILED", "error": str(e)}
            
    duration = time.time() - t0
    
    print("--------------------------------------------------")
    print(f"BATCH SUMMARY ({batch_id}):")
    print(f"  Total Rows Inserted (Silver):  {total_processed:,}")
    print(f"  Total Defective Quarantined:  {total_quarantined:,}")
    print(f"  Total Files Skipped (Idempotent): {total_skipped}")
    print(f"  Execution Duration:             {duration:.2f} seconds")
    print("==================================================")
    
    return {
        "batch_id": batch_id,
        "processed": total_processed,
        "quarantined": total_quarantined,
        "skipped": total_skipped,
        "duration": duration,
        "details": results
    }

def print_status():
    checkpoint = CheckpointStore()
    print("==================================================")
    print("NexaCore Ingestion Observability Status")
    print("==================================================")
    query = text("""
        SELECT execution_id, COALESCE(batch_id, etl_batch_id) AS batch_id, pipeline_name, source_file_name, file_checksum, 
               records_discovered, records_processed, records_quarantined, status, started_at
        FROM audit.pipeline_execution_logs
        ORDER BY started_at DESC
        LIMIT 20;
    """)
    engine = checkpoint.engine
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(r._mapping) for r in result]
        
    if not rows:
        print("No ingestion execution history found in audit logs.")
    else:
        for r in rows:
            batch_str = r['batch_id'][:20] if r['batch_id'] else 'N/A'
            file_str = r['source_file_name'][:22] if r['source_file_name'] else 'N/A'
            print(f"[{r['started_at']}] Batch={batch_str:<20} File={file_str:<22} Status={r['status']:<10} Proc={r['records_processed']:>6} Quar={r['records_quarantined']:>3}")
    print("==================================================")

def main():
    parser = argparse.ArgumentParser(description="NexaCore Data Ingestion Framework CLI")
    parser.add_argument("command", choices=["discover", "ingest", "status", "retry"], help="Command to execute")
    parser.add_argument("--input", default="data/raw/generated", help="Raw landing data directory")
    parser.add_argument("--format", default="parquet", choices=["parquet", "csv"], help="Source file format")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion bypassing SHA-256 checkpoints")
    parser.add_argument("--batch-id", help="Batch ID for retry command")
    
    args = parser.parse_args()
    
    if args.command == "discover":
        run_discovery(args.input, args.format)
    elif args.command == "ingest":
        run_ingested_batch(args.input, args.format, force=args.force)
    elif args.command == "status":
        print_status()
    elif args.command == "retry":
        if not args.batch_id:
            print("Error: --batch-id is required for retry command.")
            sys.exit(1)
        print(f"Replaying failed ingestion for batch: {args.batch_id}")
        run_ingested_batch(args.input, args.format, force=True)

if __name__ == "__main__":
    main()
