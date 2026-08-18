"""
NexaCore Data Engineering Platform — Stage 4B Phase 6
Silver-to-Gold End-to-End Reconciliation Test Suite & Pipeline Validation Engine.

Executes 5 comprehensive validation suites:
1. Fresh Pipeline Execution & System Initialization
2. Idempotency & Checkpoint Re-Execution
3. Forced Replay & UPSERT Non-Duplication
4. Silver-to-Gold Metric & Lineage Reconciliation
5. Fault Tolerance, Quarantine & Exit Code Verification
"""

import os
import sys
import json
import time
import uuid
import datetime
import subprocess
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DBT_DIR = os.path.join(PROJECT_ROOT, "dbt")
OUTPUT_REPORT_JSON = os.path.join(PROJECT_ROOT, "docs", "data-quality", "pipeline_e2e_report.json")

class E2EPipelineValidator:
    def __init__(self):
        self.results = []
        self.report = {
            "overall_status": "FAILED",
            "executed_at": datetime.datetime.now().isoformat(),
            "suites_total": 5,
            "suites_passed": 0,
            "suites_failed": 0,
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "reconciliation_variances": 0,
            "idempotency_violations": 0,
            "suite_details": {}
        }

    def record_check(self, suite_name, test_id, category, status_bool, details, metadata=None):
        status = "PASSED" if status_bool else "FAILED"
        self.report["tests_total"] += 1
        if status_bool:
            self.report["tests_passed"] += 1
        else:
            self.report["tests_failed"] += 1

        if suite_name not in self.report["suite_details"]:
            self.report["suite_details"][suite_name] = {
                "status": "PASSED",
                "tests_total": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "checks": []
            }
        
        s_detail = self.report["suite_details"][suite_name]
        s_detail["tests_total"] += 1
        if status_bool:
            s_detail["tests_passed"] += 1
        else:
            s_detail["tests_failed"] += 1
            s_detail["status"] = "FAILED"

        s_detail["checks"].append({
            "test_id": test_id,
            "category": category,
            "status": status,
            "details": details,
            "metadata": metadata or {}
        })

    def run_suite_1_fresh_execution(self):
        print("\n==================================================")
        print("SUITE 1: Fresh Pipeline Execution & System Initialization")
        print("==================================================")
        suite = "Suite_1_Fresh_Execution"
        
        # 1. Reset Database
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("TRUNCATE audit.pipeline_execution_logs CASCADE;")
            tables = [
                "customer_segments", "product_categories", "sales_channels", "machine_types", "suppliers", "warehouses",
                "customers", "products", "machines", "customer_addresses", "orders", "order_items", "inventory",
                "machine_telemetry", "maintenance_events", "failure_events", "support_tickets", "customer_satisfaction"
            ]
            for t in tables:
                cur.execute(f"TRUNCATE source.{t} CASCADE;")
            conn.commit()
            conn.close()
            self.record_check(suite, "s1_01_db_reset", "initialization", True, "Audit logs & source tables reset cleanly.")
        except Exception as e:
            self.record_check(suite, "s1_01_db_reset", "initialization", False, f"Database reset failed: {e}")
            return

        # 2. Ingest
        ingest_cmd = [sys.executable, "-m", "scripts.ingestion.cli", "ingest", "--force"]
        res_ingest = subprocess.run(ingest_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        ingest_success = (res_ingest.returncode == 0 and "152,169" in res_ingest.stdout)
        self.record_check(suite, "s1_02_ingest_execution", "ingestion", ingest_success, 
                          "Ingestion CLI executed clean batch (152,169 Silver rows inserted, 0 quarantined).",
                          {"exit_code": res_ingest.returncode})

        # 3. dbt Build
        dbt_exe = os.path.join(sys.prefix, "Scripts", "dbt.exe") if os.name == "nt" else "dbt"
        dbt_cmd = [dbt_exe, "build", "--profiles-dir", "."]
        res_dbt = subprocess.run(dbt_cmd, cwd=DBT_DIR, capture_output=True, text=True)
        dbt_success = (res_dbt.returncode == 0 and "PASS=120 WARN=0 ERROR=0" in res_dbt.stdout)
        self.record_check(suite, "s1_03_dbt_build", "transformation", dbt_success,
                          "dbt build completed successfully (120/120 PASS, 0 WARN, 0 ERROR).",
                          {"exit_code": res_dbt.returncode})

        # 4. Gold Quality Suite
        qual_cmd = [sys.executable, "scripts/gold_quality_suite.py"]
        res_qual = subprocess.run(qual_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        qual_success = (res_qual.returncode == 0 and '"overall_status": "PASSED"' in res_qual.stdout)
        self.record_check(suite, "s1_04_gold_quality_suite", "data_quality", qual_success,
                          "Gold Data Quality Suite completed with 55/55 PASS status.",
                          {"exit_code": res_qual.returncode})

    def run_suite_2_idempotency(self):
        print("\n==================================================")
        print("SUITE 2: Idempotency & Checkpoint Re-Execution")
        print("==================================================")
        suite = "Suite_2_Idempotency"
        
        # 1. Execute Ingestion WITHOUT --force
        ingest_cmd = [sys.executable, "-m", "scripts.ingestion.cli", "ingest"]
        res = subprocess.run(ingest_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        stdout_text = res.stdout
        is_skipped = ("17 files skipped" in stdout_text or "0 rows inserted" in stdout_text or "Total Files Skipped (Idempotent): 17" in stdout_text)
        self.record_check(suite, "s2_01_checkpoint_skip", "idempotency", is_skipped and res.returncode == 0,
                          "Ingestion CLI skipped all 17 previously processed parquet files via SHA-256 checkpoints.",
                          {"exit_code": res.returncode})

        # 2. Verify Database Row Counts Unchanged
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM source.orders;")
        src_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM analytics.fact_orders;")
        gold_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM analytics.dim_customer;")
        gold_cust = cur.fetchone()[0]
        conn.close()

        counts_ok = (src_orders == 10000 and gold_orders == 10000 and gold_cust == 1000)
        self.record_check(suite, "s2_02_row_counts_unmodified", "idempotency", counts_ok,
                          f"Database physical counts verified unchanged: source.orders={src_orders}, fact_orders={gold_orders}, dim_customer={gold_cust}.")

    def run_suite_3_forced_replay(self):
        print("\n==================================================")
        print("SUITE 3: Forced Replay & UPSERT Non-Duplication")
        print("==================================================")
        suite = "Suite_3_Forced_Replay"
        
        # 1. Execute Ingestion WITH --force
        ingest_cmd = [sys.executable, "-m", "scripts.ingestion.cli", "ingest", "--force"]
        res_ingest = subprocess.run(ingest_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        self.record_check(suite, "s3_01_force_ingest_replay", "upsert", res_ingest.returncode == 0,
                          "Ingestion CLI executed forced replay without SQL errors.",
                          {"exit_code": res_ingest.returncode})

        # 2. Rebuild dbt
        dbt_exe = os.path.join(sys.prefix, "Scripts", "dbt.exe") if os.name == "nt" else "dbt"
        dbt_cmd = [dbt_exe, "build", "--profiles-dir", "."]
        res_dbt = subprocess.run(dbt_cmd, cwd=DBT_DIR, capture_output=True, text=True)
        
        self.record_check(suite, "s3_02_force_dbt_rebuild", "upsert", res_dbt.returncode == 0,
                          "dbt build re-executed without primary key collision errors.",
                          {"exit_code": res_dbt.returncode})

        # 3. Assert Zero Primary Key Duplicates in Silver and Gold
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check source.orders
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT order_id) FROM source.orders;")
        so_tot, so_dist = cur.fetchone()
        so_ok = (so_tot == 10000 and so_dist == 10000)
        self.record_check(suite, "s3_03_silver_orders_no_duplicates", "upsert", so_ok,
                          f"source.orders UPSERT non-duplication: total={so_tot}, distinct={so_dist}.")

        # Check analytics.fact_orders
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT order_id) FROM analytics.fact_orders;")
        fo_tot, fo_dist = cur.fetchone()
        fo_ok = (fo_tot == 10000 and fo_dist == 10000)
        self.record_check(suite, "s3_04_gold_orders_no_duplicates", "upsert", fo_ok,
                          f"fact_orders non-duplication: total={fo_tot}, distinct={fo_dist}.")

        # Check analytics.snp_customers
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT customer_sk), COUNT(DISTINCT customer_id) FROM analytics.snp_customers;")
        sc_tot, sc_dist_sk, sc_dist_id = cur.fetchone()
        sc_ok = (sc_tot == 1000 and sc_dist_sk == 1000 and sc_dist_id == 1000)
        self.record_check(suite, "s3_05_gold_scd2_no_duplicates", "upsert", sc_ok,
                          f"snp_customers non-duplication: total={sc_tot}, distinct_sk={sc_dist_sk}, distinct_id={sc_dist_id}.")

        conn.close()

    def run_suite_4_reconciliation(self):
        print("\n==================================================")
        print("SUITE 4: Silver-to-Gold Metric & Lineage Reconciliation")
        print("==================================================")
        suite = "Suite_4_Metric_Reconciliation"
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Orders & Revenue Reconciliation
        cur.execute("SELECT COUNT(*) AS cnt, SUM(total_amount)::numeric(18,2) AS rev FROM source.orders;")
        s_ord = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt, SUM(total_amount)::numeric(18,2) AS rev FROM analytics.fact_orders;")
        g_ord = cur.fetchone()
        
        ord_cnt_diff = abs(s_ord["cnt"] - g_ord["cnt"])
        ord_rev_diff = abs(float(s_ord["rev"]) - float(g_ord["rev"]))
        ord_ok = (ord_cnt_diff == 0 and ord_rev_diff == 0.0)
        if not ord_ok:
            self.report["reconciliation_variances"] += 1
        self.record_check(suite, "s4_01_orders_revenue_reconciled", "financial_reconciliation", ord_ok,
                          f"Orders reconciliation: Silver count={s_ord['cnt']}, rev=${s_ord['rev']} | Gold count={g_ord['cnt']}, rev=${g_ord['rev']} (Diff: cnt={ord_cnt_diff}, rev=${ord_rev_diff:.2f}).")

        # 2. Line Items & Net Revenue Reconciliation
        cur.execute("SELECT COUNT(*) AS cnt, SUM(quantity) AS qty, SUM(unit_price * quantity - discount_amount)::numeric(18,2) AS net_rev FROM source.order_items;")
        s_item = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt, SUM(quantity) AS qty, SUM(net_revenue)::numeric(18,2) AS net_rev FROM analytics.fact_order_items;")
        g_item = cur.fetchone()

        item_cnt_diff = abs(s_item["cnt"] - g_item["cnt"])
        item_qty_diff = abs(s_item["qty"] - g_item["qty"])
        item_rev_diff = abs(float(s_item["net_rev"]) - float(g_item["net_rev"]))
        item_ok = (item_cnt_diff == 0 and item_qty_diff == 0 and item_rev_diff == 0.0)
        if not item_ok:
            self.report["reconciliation_variances"] += 1
        self.record_check(suite, "s4_02_order_items_reconciled", "financial_reconciliation", item_ok,
                          f"Order Items reconciliation: Silver count={s_item['cnt']}, qty={s_item['qty']}, net_rev=${s_item['net_rev']} | Gold count={g_item['cnt']}, qty={g_item['qty']}, net_rev=${g_item['net_rev']}.")

        # 3. Inventory On-Hand & Allocation Reconciliation
        cur.execute("SELECT COUNT(*) AS cnt, SUM(quantity_on_hand) AS on_hand, SUM(quantity_allocated) AS alloc FROM source.inventory;")
        s_inv = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt, SUM(quantity_on_hand) AS on_hand, SUM(quantity_allocated) AS alloc FROM analytics.fact_inventory_snapshot;")
        g_inv = cur.fetchone()

        inv_cnt_diff = abs(s_inv["cnt"] - g_inv["cnt"])
        inv_oh_diff = abs(s_inv["on_hand"] - g_inv["on_hand"])
        inv_al_diff = abs(s_inv["alloc"] - g_inv["alloc"])
        inv_ok = (inv_cnt_diff == 0 and inv_oh_diff == 0 and inv_al_diff == 0)
        if not inv_ok:
            self.report["reconciliation_variances"] += 1
        self.record_check(suite, "s4_03_inventory_reconciled", "inventory_reconciliation", inv_ok,
                          f"Inventory reconciliation: Silver count={s_inv['cnt']}, on_hand={s_inv['on_hand']}, alloc={s_inv['alloc']} | Gold count={g_inv['cnt']}, on_hand={g_inv['on_hand']}, alloc={g_inv['alloc']}.")

        # 4. Support Tickets & CSAT Surveys Reconciliation
        cur.execute("SELECT COUNT(*) AS cnt FROM source.support_tickets;")
        s_tkt_cnt = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM source.customer_satisfaction;")
        s_csat_cnt = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS tkt_cnt, COUNT(csat_score) AS csat_cnt, AVG(csat_score)::numeric(10,2) AS avg_csat FROM analytics.fact_support_tickets;")
        g_tkt = cur.fetchone()

        tkt_diff = abs(s_tkt_cnt - g_tkt["tkt_cnt"])
        csat_diff = abs(s_csat_cnt - g_tkt["csat_cnt"])
        csat_ok = (tkt_diff == 0 and csat_diff == 0 and float(g_tkt["avg_csat"]) == 4.15)
        if not csat_ok:
            self.report["reconciliation_variances"] += 1
        self.record_check(suite, "s4_04_support_csat_reconciled", "support_reconciliation", csat_ok,
                          f"Support & CSAT reconciliation: Silver tickets={s_tkt_cnt}, csat={s_csat_cnt} | Gold tickets={g_tkt['tkt_cnt']}, linked_csat={g_tkt['csat_cnt']}, avg_score={g_tkt['avg_csat']}.")

        # 5. Machine Telemetry Preservation & Rollup Reconciliation
        cur.execute("SELECT COUNT(*) AS raw_cnt, COUNT(DISTINCT machine_id) AS m_cnt FROM source.machine_telemetry;")
        s_tel = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS rollup_cnt, COUNT(DISTINCT machine_id) AS m_cnt FROM analytics.fact_machine_telemetry;")
        g_tel = cur.fetchone()

        tel_ok = (s_tel["raw_cnt"] == 100000 and g_tel["rollup_cnt"] == 29800 and s_tel["m_cnt"] == 50 and g_tel["m_cnt"] == 50)
        if not tel_ok:
            self.report["reconciliation_variances"] += 1
        self.record_check(suite, "s4_05_telemetry_rollup_reconciled", "telemetry_reconciliation", tel_ok,
                          f"Telemetry reconciliation: Silver raw={s_tel['raw_cnt']}, machines={s_tel['m_cnt']} | Gold 1-min rollups={g_tel['rollup_cnt']}, machines={g_tel['m_cnt']} (Aggregation ratio 3.36:1).")

        conn.close()

    def run_suite_5_fault_tolerance(self):
        print("\n==================================================")
        print("SUITE 5: Fault Tolerance, Quarantine & Exit Code Verification")
        print("==================================================")
        suite = "Suite_5_Fault_Tolerance"
        
        # 1. Verify Quality Validator Engine Logic on Invalid Record
        from scripts.ingestion.validation import QualityValidator
        validator = QualityValidator()
        
        # Test invalid customer record (missing customer_id and invalid email format)
        invalid_cust_df = pd.DataFrame([
            {"customer_id": None, "email": "invalid-email-string", "created_at": "2026-01-01T00:00:00"},
            {"customer_id": "a0000000-0000-0000-0000-000000000001", "email": "valid@example.com", "created_at": "2026-01-01T00:00:00"}
        ])
        
        valid_df, invalid_records = validator.validate_entity("customers", invalid_cust_df)
        val_ok = (len(valid_df) == 1 and len(invalid_records) == 1)
        self.record_check(suite, "s5_01_contract_validator_isolation", "fault_tolerance", val_ok,
                          f"QualityValidator isolated contract breach: valid_rows={len(valid_df)}, quarantined_records={len(invalid_records)}.")

        # 2. Verify Exit Code Behavior for CLI Commands
        res_help = subprocess.run([sys.executable, "-m", "scripts.ingestion.cli", "--help"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        help_ok = (res_help.returncode == 0)
        self.record_check(suite, "s5_02_cli_success_exit_code", "orchestration", help_ok,
                          "Ingestion CLI returns exit code 0 on valid command execution.")

        res_invalid = subprocess.run([sys.executable, "-m", "scripts.ingestion.cli", "invalid_subcommand"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        err_ok = (res_invalid.returncode != 0)
        self.record_check(suite, "s5_03_cli_failure_exit_code", "orchestration", err_ok,
                          f"Ingestion CLI returns non-zero exit code ({res_invalid.returncode}) on invalid command invocation.")

    def run_all(self):
        t0 = time.time()
        self.run_suite_1_fresh_execution()
        self.run_suite_2_idempotency()
        self.run_suite_3_forced_replay()
        self.run_suite_4_reconciliation()
        self.run_suite_5_fault_tolerance()
        
        duration = time.time() - t0
        self.report["execution_duration_sec"] = round(duration, 2)
        
        # Calculate suite pass/fail totals
        passed_suites = 0
        failed_suites = 0
        for s_name, s_info in self.report["suite_details"].items():
            if s_info["status"] == "PASSED":
                passed_suites += 1
            else:
                failed_suites += 1
        
        self.report["suites_passed"] = passed_suites
        self.report["suites_failed"] = failed_suites
        
        if self.report["tests_failed"] == 0 and self.report["suites_failed"] == 0:
            self.report["overall_status"] = "PASSED"
        else:
            self.report["overall_status"] = "FAILED"

        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_REPORT_JSON), exist_ok=True)
        report_str = json.dumps(self.report, indent=2)
        with open(OUTPUT_REPORT_JSON, "w", encoding="utf-8") as f:
            f.write(report_str)
            f.flush()
            os.fsync(f.fileno())

        print("\n==================================================")
        print(f"E2E PIPELINE VALIDATION SUMMARY: {self.report['overall_status']}")
        print("==================================================")
        print(f"Suites Evaluated: {self.report['suites_total']} | Passed: {self.report['suites_passed']} | Failed: {self.report['suites_failed']}")
        print(f"Tests Evaluated:  {self.report['tests_total']} | Passed: {self.report['tests_passed']} | Failed: {self.report['tests_failed']}")
        print(f"Reconciliation Variances: {self.report['reconciliation_variances']}")
        print(f"Report JSON Saved To:     {OUTPUT_REPORT_JSON}")
        print("==================================================")

        return 0 if self.report["overall_status"] == "PASSED" else 1

if __name__ == "__main__":
    validator = E2EPipelineValidator()
    sys.exit(validator.run_all())
