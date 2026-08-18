"""
CI Database & Data Lifecycle Bootstrap Orchestrator
===================================================
Automates the full end-to-end data lifecycle for fresh CI environments:
1. Synthetic Data Generation (scripts.enterprise_data_generator -> data/raw/generated/*.parquet)
2. Database Schemas & DDL Initialization (docker/postgres/init & sql/schema)
3. Reference Table Seeding (source.sales_channels)
4. Medallion Bronze/Silver Ingestion (scripts.ingestion.cli)
5. Gold Feature Mart & Dimensional Modeling Transformation (dbt build)
6. Feature Mart & Prediction Store Row Audit
7. Batch Inference Engine Execution (data_science.mlops.batch_inference)
8. Multi-Agent Decision Seeding (data_science.agents.agent_bus)
"""

import sys
import os
import glob
import logging
import psycopg2
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.config import DB_CONFIG
from data_science.db import get_engine, read_sql
from data_science.mlops.batch_inference import BatchInferenceEngine
from data_science.agents.agent_bus import AgentBus

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ci_init_database")

def init_ci_database():
    logger.info("==================================================")
    logger.info("STEP 1: Generating Synthetic Raw Parquet Dataset...")
    logger.info("==================================================")
    from scripts.enterprise_data_generator.cli import generate_dataset
    from scripts.enterprise_data_generator.writers import ParquetWriter

    raw_dir = "data/raw/generated"
    os.makedirs(raw_dir, exist_ok=True)
    dataset = generate_dataset(profile="development", seed=42, corrupt_rate=0.0)
    writer = ParquetWriter()
    writer.write(dataset, raw_dir)

    # Verify file discovery immediately
    raw_files = glob.glob(os.path.join(raw_dir, "*.parquet"))
    logger.info(f"[OK] Generated {len(raw_files)} raw parquet files in {raw_dir}.")
    if len(raw_files) == 0:
        raise RuntimeError("CRITICAL ERROR: Synthetic data generation produced 0 files!")

    logger.info("\n==================================================")
    logger.info("STEP 2: Initializing PostgreSQL Schemas & Core DDL...")
    logger.info("==================================================")
    init_sql_files = sorted(glob.glob("docker/postgres/init/*.sql"))
    schema_sql_files = sorted(glob.glob("sql/schema/*.sql"))
    all_sql_files = init_sql_files + schema_sql_files

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for sql_file in all_sql_files:
        logger.info(f"Applying SQL DDL file: {sql_file}")
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        try:
            cur.execute(sql_content)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning(f"Note on DDL file {sql_file}: {e}")

    logger.info("\n==================================================")
    logger.info("STEP 3: Seeding Reference Tables (source.sales_channels)...")
    logger.info("==================================================")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO source.sales_channels (channel_id, channel_code, channel_name, commission_rate) VALUES
        (1, 'DIRECT', 'Direct Enterprise Sales', 0.0500),
        (2, 'PARTNER', 'Partner Channel Network', 0.1000),
        (3, 'ONLINE', 'Digital Self-Service Portal', 0.0200)
        ON CONFLICT (channel_id) DO NOTHING;
    """)
    conn.commit()
    conn.close()

    logger.info("\n==================================================")
    logger.info("STEP 4: Executing Medallion Bronze/Silver Ingestion...")
    logger.info("==================================================")
    from scripts.ingestion.cli import run_ingested_batch
    ingest_res = run_ingested_batch(input_dir=raw_dir, file_format="parquet", force=True)
    logger.info(f"[OK] Ingestion result: {ingest_res}")

    logger.info("\n==================================================")
    logger.info("STEP 5: Executing dbt Gold Transformations...")
    logger.info("==================================================")
    from dbt.cli.main import dbtRunner
    dbt_res = dbtRunner().invoke(["build", "--project-dir", "dbt", "--profiles-dir", "dbt"])
    logger.info(f"[OK] dbt build result: success={dbt_res.success}")
    if not dbt_res.success:
        raise RuntimeError(f"CRITICAL ERROR: dbt build failed! Result: {dbt_res}")

    engine = get_engine()

    logger.info("\n==================================================")
    logger.info("STEP 6: Executing Batch Inference Engine...")
    logger.info("==================================================")
    batch_engine = BatchInferenceEngine(db_engine=engine)
    results = batch_engine.run_all_batch_inferences()
    logger.info(f"[OK] Batch inference result: {results}")

    logger.info("\n==================================================")
    logger.info("STEP 7: Executing AgentBus Orchestrator...")
    logger.info("==================================================")
    bus = AgentBus(db_engine=engine)
    bus_results = bus.run()
    logger.info(f"[OK] AgentBus completed: {len(bus_results)} decisions generated.")

    logger.info("\n==================================================")
    logger.info("DATA BOOTSTRAP DIAGNOSTIC AUDIT")
    logger.info("==================================================")
    
    logger.info("SOURCE TABLES:")
    for tbl in ["source.customers", "source.orders", "source.order_items", "source.inventory", "source.machine_telemetry"]:
        cnt = read_sql(f"SELECT COUNT(*) FROM {tbl};", engine).iloc[0, 0]
        logger.info(f"  - {tbl:<35} = {cnt:>7} rows")

    logger.info("\nML FEATURE MARTS:")
    for mart in [
        "analytics.ml_customer_churn_features",
        "analytics.ml_demand_forecasting_daily",
        "analytics.ml_inventory_stockout_risk",
        "analytics.ml_machine_telemetry_features"
    ]:
        cnt = read_sql(f"SELECT COUNT(*) FROM {mart};", engine).iloc[0, 0]
        logger.info(f"  - {mart:<40} = {cnt:>7} rows")

    logger.info("\nPREDICTION TABLES:")
    for pred in [
        "analytics.fact_predictions_customer_churn",
        "analytics.fact_predictions_sku_demand",
        "analytics.fact_predictions_inventory_stockout",
        "analytics.fact_predictions_machine_health",
        "analytics.agent_decisions"
    ]:
        cnt = read_sql(f"SELECT COUNT(*) FROM {pred};", engine).iloc[0, 0]
        logger.info(f"  - {pred:<45} = {cnt:>7} rows")

    logger.info("==================================================")
    logger.info("CI DATABASE & DATA LIFECYCLE BOOTSTRAP COMPLETE")
    logger.info("==================================================")

if __name__ == "__main__":
    init_ci_database()
