"""
Quarantine Dead-Letter Writer.
Inserts raw contract-violating records into audit.quarantine_records.
"""

import json
from sqlalchemy import text
from ..postgres import get_engine

class QuarantineWriter:
    def __init__(self):
        self.engine = get_engine()

    def write_quarantine(self, batch_id: str, source_file: str, entity_name: str, invalid_records: list) -> int:
        if not invalid_records:
            return 0
            
        insert_query = text("""
            INSERT INTO audit.quarantine_records (
                batch_id, etl_batch_id, source_file, entity_name, source_table, 
                failed_rule, quarantine_reason, raw_record_json, quarantined_at
            )
            VALUES (
                :batch_id, :batch_id, :source_file, :entity_name, :entity_name, 
                :failed_rule, :failed_rule, :raw_record_json, NOW()
            );
        """)
        
        quarantine_count = 0
        with self.engine.begin() as conn:
            for item in invalid_records:
                rule = item.get("failed_rule", "UNKNOWN_VALIDATION_ERROR")
                payload_json = json.dumps(item.get("row_dict", {}), default=str)
                
                conn.execute(insert_query, {
                    "batch_id": batch_id,
                    "source_file": source_file,
                    "entity_name": entity_name,
                    "failed_rule": rule,
                    "raw_record_json": payload_json
                })
                quarantine_count += 1
                
        return quarantine_count
