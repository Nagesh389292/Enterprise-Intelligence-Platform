"""
Checkpoint Store Manager.
Queries audit.pipeline_execution_logs to detect processed files and prevent duplicate batch executions.
"""

from sqlalchemy import text
from ..postgres import get_engine

class CheckpointStore:
    def __init__(self):
        self.engine = get_engine()

    def is_file_processed(self, file_name: str, file_checksum: str) -> bool:
        """Returns True if file with matching SHA-256 checksum has completed status."""
        query = text("""
            SELECT COUNT(*) 
            FROM audit.pipeline_execution_logs 
            WHERE source_file_name = :file_name 
              AND file_checksum = :checksum 
              AND status = 'COMPLETED';
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"file_name": file_name, "checksum": file_checksum})
            count = result.scalar()
            return count > 0

    def get_latest_execution_history(self, file_name: str) -> list:
        """Returns execution history log records for a given file name."""
        query = text("""
            SELECT execution_id AS log_id, COALESCE(batch_id, etl_batch_id) AS batch_id, 
                   pipeline_name, source_file_name, file_checksum, 
                   records_discovered, records_processed, records_quarantined, status, 
                   started_at, completed_at, error_message
            FROM audit.pipeline_execution_logs
            WHERE source_file_name = :file_name
            ORDER BY started_at DESC;
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"file_name": file_name})
            return [dict(row._mapping) for row in result]
