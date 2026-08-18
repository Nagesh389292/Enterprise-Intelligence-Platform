"""
CLI Execution Script: Production Batch Inference & Prediction Store Persistence
================================================================================
Applies SQL prediction table DDL and executes batch inference pipelines for all 4 models,
persisting outputs to analytics.fact_predictions_*.
"""

import sys
import os
import logging
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.db import get_engine
from data_science.mlops.batch_inference import BatchInferenceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def apply_prediction_schema(engine):
    logger.info("Applying PostgreSQL Prediction Store DDL (sql/schema/09_predictions_store.sql)...")
    ddl_path = "sql/schema/09_predictions_store.sql"
    if not os.path.exists(ddl_path):
        logger.warning(f"DDL file {ddl_path} not found.")
        return

    with open(ddl_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split by semicolon or execute directly
    with engine.begin() as conn:
        for stmt in sql_content.split(";"):
            stmt_clean = stmt.strip()
            if stmt_clean:
                conn.execute(text(stmt_clean))
    logger.info("Successfully applied Prediction Store DDL.")

def main():
    engine = get_engine()
    apply_prediction_schema(engine)

    batch_engine = BatchInferenceEngine(db_engine=engine)
    results = batch_engine.run_all_batch_inferences()

    print("\n================================================================================")
    print("BATCH INFERENCE PIPELINE COMPLETED")
    print("================================================================================")
    for domain, res in results.items():
        print(f"  - Domain: {domain:<18} | Status: {res.get('status')} | Records: {res.get('records_written', 0)}")
    print("================================================================================")

if __name__ == "__main__":
    main()
