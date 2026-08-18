"""
Audit Execution Logger Manager.
Records execution logs in audit.pipeline_execution_logs and assertion logs in audit.data_quality_audit_logs.
"""

from sqlalchemy import text
from ..postgres import get_engine

class AuditLogger:
    def __init__(self):
        self.engine = get_engine()
        self.ensure_audit_schema()

    def ensure_audit_schema(self):
        """Ensures audit schema tables contain required ingestion columns."""
        with self.engine.begin() as conn:
            # Audit execution logs
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS batch_id VARCHAR(64);"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS source_file_name VARCHAR(255);"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS file_checksum VARCHAR(64);"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS records_discovered INT DEFAULT 0;"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS records_processed INT DEFAULT 0;"))
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs ADD COLUMN IF NOT EXISTS records_quarantined INT DEFAULT 0;"))
            
            # Make sure CHECK constraints on status don't block IN_PROGRESS/COMPLETED
            conn.execute(text("ALTER TABLE audit.pipeline_execution_logs DROP CONSTRAINT IF EXISTS pipeline_execution_logs_status_check;"))
            
            # Audit quarantine records
            conn.execute(text("ALTER TABLE audit.quarantine_records ADD COLUMN IF NOT EXISTS batch_id VARCHAR(64);"))
            conn.execute(text("ALTER TABLE audit.quarantine_records ADD COLUMN IF NOT EXISTS source_file VARCHAR(255);"))
            conn.execute(text("ALTER TABLE audit.quarantine_records ADD COLUMN IF NOT EXISTS entity_name VARCHAR(100);"))
            conn.execute(text("ALTER TABLE audit.quarantine_records ADD COLUMN IF NOT EXISTS failed_rule VARCHAR(100);"))

    def start_file_log(
        self,
        batch_id: str,
        pipeline_name: str,
        source_file_name: str,
        file_checksum: str,
        file_size_bytes: int,
        records_discovered: int
    ) -> int:
        query = text("""
            INSERT INTO audit.pipeline_execution_logs (
                batch_id, etl_batch_id, pipeline_name, source_layer, target_table, 
                source_file_name, file_checksum, file_size_bytes,
                records_discovered, records_processed, records_quarantined, status, started_at
            )
            VALUES (
                :batch_id, :batch_id, :pipeline_name, 'BRONZE', :source_file_name,
                :source_file_name, :file_checksum, :file_size_bytes,
                :records_discovered, 0, 0, 'IN_PROGRESS', NOW()
            )
            RETURNING execution_id;
        """)
        with self.engine.begin() as conn:
            result = conn.execute(query, {
                "batch_id": batch_id,
                "pipeline_name": pipeline_name,
                "source_file_name": source_file_name,
                "file_checksum": file_checksum,
                "file_size_bytes": file_size_bytes,
                "records_discovered": records_discovered
            })
            return result.scalar()

    def complete_file_log(self, log_id: int, records_processed: int, records_quarantined: int):
        query = text("""
            UPDATE audit.pipeline_execution_logs
            SET status = 'COMPLETED',
                records_processed = :records_processed,
                records_ingested = :records_processed,
                records_quarantined = :records_quarantined,
                records_rejected = :records_quarantined,
                completed_at = NOW()
            WHERE execution_id = :log_id;
        """)
        with self.engine.begin() as conn:
            conn.execute(query, {
                "log_id": log_id,
                "records_processed": records_processed,
                "records_quarantined": records_quarantined
            })

    def fail_file_log(self, log_id: int, error_message: str):
        query = text("""
            UPDATE audit.pipeline_execution_logs
            SET status = 'FAILED',
                error_message = :error_message,
                completed_at = NOW()
            WHERE execution_id = :log_id;
        """)
        with self.engine.begin() as conn:
            conn.execute(query, {
                "log_id": log_id,
                "error_message": error_message[:2000]
            })

    def log_quality_assertion(
        self,
        batch_id: str,
        table_name: str,
        rule_name: str,
        evaluated: int,
        passed: int,
        failed: int
    ):
        query = text("""
            INSERT INTO audit.data_quality_audit_logs (
                etl_batch_id, table_name, rule_name, rule_type, records_tested, records_failed, assertion_status, executed_at
            )
            VALUES (
                :batch_id, :table_name, :rule_name, 'CONTRACT_CHECK', :evaluated, :failed,
                CASE WHEN :failed = 0 THEN 'PASSED' ELSE 'FAILED' END, NOW()
            );
        """)
        with self.engine.begin() as conn:
            conn.execute(query, {
                "batch_id": batch_id,
                "table_name": table_name,
                "rule_name": rule_name,
                "evaluated": evaluated,
                "failed": failed
            })
