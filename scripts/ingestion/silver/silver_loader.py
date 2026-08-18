"""
Silver Layer Grain-Aware Idempotent PostgreSQL Loader.
Performs batch UPSERT inserts into source.* tables, enforcing deduplication at the entity grain.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
from sqlalchemy import text
from ..postgres import get_engine

def sanitize_record(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes row dict parameters so NaN/NaT values become SQL NULL (None)."""
    sanitized = {}
    for k, v in row_dict.items():
        if pd.isna(v) or v is None:
            sanitized[k] = None
        elif isinstance(v, str) and v.lower() in ("nan", "none", "<na>", "null"):
            sanitized[k] = None
        else:
            sanitized[k] = v
    return sanitized

class SilverLoader:
    def __init__(self):
        self.engine = get_engine()
        self.ensure_lineage_columns()

    def ensure_lineage_columns(self):
        """Ensures standard audit lineage columns exist on source.* tables."""
        tables = [
            "customer_segments", "customers", "customer_addresses", "product_categories",
            "products", "suppliers", "warehouses", "orders", "order_items", "inventory",
            "machine_types", "machines", "machine_telemetry", "maintenance_events",
            "failure_events", "support_tickets", "customer_satisfaction"
        ]
        
        with self.engine.begin() as conn:
            for tbl in tables:
                conn.execute(text(f"ALTER TABLE source.{tbl} ADD COLUMN IF NOT EXISTS _ingestion_batch_id VARCHAR(64);"))
                conn.execute(text(f"ALTER TABLE source.{tbl} ADD COLUMN IF NOT EXISTS _source_file VARCHAR(255);"))
                conn.execute(text(f"ALTER TABLE source.{tbl} ADD COLUMN IF NOT EXISTS _source_checksum VARCHAR(64);"))
                conn.execute(text(f"ALTER TABLE source.{tbl} ADD COLUMN IF NOT EXISTS _ingested_at TIMESTAMPTZ DEFAULT NOW();"))

    def load_entity(
        self,
        entity_name: str,
        df: pd.DataFrame,
        batch_id: str,
        source_file: str,
        source_checksum: str
    ) -> int:
        if df.empty:
            return 0

        # Inject lineage metadata columns
        df = df.copy()
        df["_ingestion_batch_id"] = batch_id
        df["_source_file"] = source_file
        df["_source_checksum"] = source_checksum
        
        table_name = entity_name
        
        # Determine UPSERT conflict target column(s) based on entity grain
        conflict_keys = {
            "customer_segments": "segment_id",
            "customers": "customer_id",
            "customer_addresses": "address_id",
            "product_categories": "category_id",
            "products": "product_id",
            "suppliers": "supplier_id",
            "warehouses": "warehouse_id",
            "orders": "order_id",
            "order_items": "order_item_id",
            "inventory": "inventory_id",
            "machine_types": "machine_type_id",
            "machines": "machine_id",
            "machine_telemetry": "telemetry_id",
            "maintenance_events": "maintenance_id",
            "failure_events": "failure_id",
            "support_tickets": "ticket_id",
            "customer_satisfaction": "survey_id"
        }
        
        key_col = conflict_keys.get(table_name)
        if key_col and key_col in df.columns:
            # In-memory deduplication on conflict key to prevent ON CONFLICT DO UPDATE batch collision
            df = df.drop_duplicates(subset=[key_col], keep="last")

        columns = list(df.columns)
        col_names_str = ", ".join(columns)
        val_params_str = ", ".join([f":{c}" for c in columns])
        
        # Convert records and sanitize NaN -> None
        raw_records = df.to_dict(orient="records")
        records = [sanitize_record(r) for r in raw_records]

        if not key_col or key_col not in columns:
            insert_sql = text(f"INSERT INTO source.{table_name} ({col_names_str}) VALUES ({val_params_str});")
            with self.engine.begin() as conn:
                conn.execute(insert_sql, records)
            return len(records)

        # Build UPDATE SET clause for non-key columns
        update_cols = [c for c in columns if c != key_col and c != "_ingested_at"]
        update_set_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        update_set_str += ", _ingested_at = NOW()"

        upsert_sql = text(f"""
            INSERT INTO source.{table_name} ({col_names_str})
            VALUES ({val_params_str})
            ON CONFLICT ({key_col})
            DO UPDATE SET {update_set_str};
        """)

        with self.engine.begin() as conn:
            conn.execute(upsert_sql, records)

        return len(records)
