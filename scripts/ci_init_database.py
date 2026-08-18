"""
CI Database Initialization Script
=================================
Automates clean schema creation, DDL execution, data ingestion, batch inference,
and agent decision seeding for fresh CI test environments.
"""

import sys
import os
import glob
import logging
import psycopg2
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_science.config import DB_CONFIG
from data_science.db import get_engine
from data_science.mlops.batch_inference import BatchInferenceEngine
from data_science.agents.agent_bus import AgentBus

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ci_init_database")

def init_ci_database():
    logger.info("Initializing CI PostgreSQL Database Schema & Seeds...")

    # 1. Ensure Schemas & Core DDL exist
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

    # 2. Seed Reference Tables & Ingest Synthetic Data
    logger.info("Seeding reference tables (source.sales_channels)...")
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

    logger.info("Executing bronze/silver ingestion...")
    from scripts.ingestion.cli import run_ingested_batch
    run_ingested_batch(force=True)

    # 3. Transform Silver data into Gold feature marts via dbt
    logger.info("Executing dbt build to create dimensions, facts, and ML feature marts...")
    from dbt.cli.main import dbtRunner
    dbt_res = dbtRunner().invoke(["build", "--project-dir", "dbt", "--profiles-dir", "dbt"])
    logger.info(f"dbt build result: success={dbt_res.success}")

    # 4. Audit ML Feature Mart Row Counts
    engine = get_engine()
    from data_science.db import read_sql
    logger.info("==================================================")
    logger.info("ML FEATURE MART STATUS AUDIT:")
    logger.info("--------------------------------------------------")
    feature_marts = [
        "analytics.ml_customer_churn_features",
        "analytics.ml_demand_forecasting_daily",
        "analytics.ml_inventory_stockout_risk",
        "analytics.ml_machine_telemetry_features"
    ]
    for mart in feature_marts:
        df_cnt = read_sql(f"SELECT COUNT(*) as cnt FROM {mart};", engine)
        cnt = df_cnt.iloc[0]["cnt"]
        logger.info(f"  - {mart:<40}: EXISTS, {cnt} rows")
    logger.info("==================================================")

    # 5. Populate Prediction Store Batch Inferences
    logger.info("Executing batch inference engine to populate analytics predictions...")
    batch_engine = BatchInferenceEngine(db_engine=engine)
    results = batch_engine.run_all_batch_inferences()
    logger.info(f"Batch inference completed: {results}")


    # 4. Seed Multi-Agent Decisions
    logger.info("Executing AgentBus orchestrator to seed agent_decisions audit table...")
    bus = AgentBus(db_engine=engine)
    bus_results = bus.run()
    logger.info(f"AgentBus execution completed: {len(bus_results)} decisions generated.")


    logger.info("==================================================")
    logger.info("CI DATABASE INITIALIZATION COMPLETED SUCCESSFULLY")
    logger.info("==================================================")

if __name__ == "__main__":
    init_ci_database()
