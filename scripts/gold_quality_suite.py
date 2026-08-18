"""
NexaCore Data Platform - Gold Data Quality & Governance Audit Suite (Stage 4B Phase 5)
Validates structural integrity, referential integrity, business rules, SCD2 invariants,
cross-fact control totals reconciliation, telemetry quality, null profiles, and domain ranges.
Outputs machine-readable gold_quality_report.json and exits non-zero on critical error.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import sys
from datetime import datetime

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

def run_gold_quality_suite():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    warnings = 0
    
    null_violations = 0
    referential_violations = 0
    business_rule_violations = 0
    temporal_violations = 0
    reconciliation_variances = 0
    orphan_records = 0
    
    test_results = []

    def record_check(test_name, category, passed, detail, critical=True):
        nonlocal total_tests, passed_tests, failed_tests, warnings
        nonlocal null_violations, referential_violations, business_rule_violations, temporal_violations
        
        total_tests += 1
        if passed:
            passed_tests += 1
            status = "PASS"
        else:
            if critical:
                failed_tests += 1
                status = "FAIL"
                if category == "null": null_violations += 1
                elif category == "referential": referential_violations += 1
                elif category == "business_rule": business_rule_violations += 1
                elif category == "temporal": temporal_violations += 1
            else:
                warnings += 1
                status = "WARN"

        test_results.append({
            "test_name": test_name,
            "category": category,
            "status": status,
            "detail": detail
        })

    # ==================================================
    # A. STRUCTURAL & GRAIN INTEGRITY
    # ==================================================
    # 1. Models & Table Existence
    expected_tables = [
        "dim_date", "dim_customer", "dim_product", "dim_supplier", "dim_warehouse", "dim_machine",
        "fact_orders", "fact_order_items", "fact_inventory_snapshot", "fact_machine_telemetry",
        "fact_maintenance_events", "fact_support_tickets", "snp_customers"
    ]
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'analytics' AND table_type = 'BASE TABLE';
    """)
    existing_tables = set(r["table_name"] for r in cur.fetchall())
    
    missing_tables = set(expected_tables) - existing_tables
    record_check("table_existence", "structural", len(missing_tables) == 0, 
                 f"Expected 13 tables, missing: {list(missing_tables)}")

    # 2. Key Uniqueness & Grains
    grain_checks = [
        ("dim_date", "date_key", 1095),
        ("dim_customer", "customer_id", 1000),
        ("snp_customers", "customer_sk", 1000),
        ("dim_product", "product_id", 100),
        ("dim_supplier", "supplier_id", 25),
        ("dim_warehouse", "warehouse_id", 5),
        ("dim_machine", "machine_id", 50),
        ("fact_orders", "order_id", 10000),
        ("fact_order_items", "order_item_id", 35193),
        ("fact_inventory_snapshot", "inventory_id", 500),
        ("fact_machine_telemetry", "telemetry_minute_key", 29800),
        ("fact_maintenance_events", "maintenance_id", 10),
        ("fact_support_tickets", "ticket_id", 2500)
    ]
    for tbl, pk, exp_cnt in grain_checks:
        cur.execute(f"SELECT COUNT(*) AS total, COUNT(DISTINCT {pk}) AS dist_pk FROM analytics.{tbl};")
        res = cur.fetchone()
        is_unique = res["total"] == res["dist_pk"] == exp_cnt
        record_check(f"grain_uniqueness_{tbl}", "structural", is_unique, 
                     f"Table analytics.{tbl}: total={res['total']}, distinct_{pk}={res['dist_pk']}, expected={exp_cnt}")

    # ==================================================
    # B. REFERENTIAL INTEGRITY & ORPHANS
    # ==================================================
    fk_checks = [
        ("fact_orders", "customer_id", "dim_customer", "customer_id"),
        ("fact_orders", "date_key", "dim_date", "date_key"),
        ("fact_order_items", "order_id", "fact_orders", "order_id"),
        ("fact_order_items", "product_id", "dim_product", "product_id"),
        ("fact_inventory_snapshot", "warehouse_id", "dim_warehouse", "warehouse_id"),
        ("fact_inventory_snapshot", "product_id", "dim_product", "product_id"),
        ("fact_machine_telemetry", "machine_id", "dim_machine", "machine_id"),
        ("fact_maintenance_events", "machine_id", "dim_machine", "machine_id"),
        ("fact_support_tickets", "customer_id", "dim_customer", "customer_id"),
        ("fact_support_tickets", "customer_id", "snp_customers", "customer_id")
    ]
    for f_tbl, f_col, d_tbl, d_col in fk_checks:
        cur.execute(f"""
            SELECT COUNT(*) AS orphan_cnt 
            FROM analytics.{f_tbl} f 
            LEFT JOIN analytics.{d_tbl} d ON f.{f_col} = d.{d_col} 
            WHERE d.{d_col} IS NULL AND f.{f_col} IS NOT NULL;
        """)
        orphans = cur.fetchone()["orphan_cnt"]
        if orphans > 0: orphan_records += orphans
        record_check(f"referential_integrity_{f_tbl}_{f_col}", "referential", orphans == 0, 
                     f"FK analytics.{f_tbl}.{f_col} -> analytics.{d_tbl}.{d_col}: {orphans} orphans found")

    # ==================================================
    # C. BUSINESS RULE TESTS
    # ==================================================
    # 1. Orders Rules
    cur.execute("SELECT COUNT(*) AS bad_rev FROM analytics.fact_orders WHERE total_amount < 0;")
    bad_order_rev = cur.fetchone()["bad_rev"]
    record_check("business_rule_orders_non_negative_total", "business_rule", bad_order_rev == 0, f"Negative order total_amount rows: {bad_order_rev}")

    cur.execute("SELECT COUNT(*) AS bad_delay FROM analytics.fact_orders WHERE derived_delivery_delay_days < -365 OR derived_delivery_delay_days > 365;")
    bad_delays = cur.fetchone()["bad_delay"]
    record_check("business_rule_orders_valid_delivery_delay", "business_rule", bad_delays == 0, f"Out-of-range delivery delay days rows: {bad_delays}")

    # 2. Order Items Rules
    cur.execute("""
        SELECT COUNT(*) AS bad_math 
        FROM analytics.fact_order_items 
        WHERE (gross_revenue - discount_amount) <> net_revenue 
           OR discount_amount > gross_revenue 
           OR quantity <= 0 
           OR unit_price < 0;
    """)
    bad_item_math = cur.fetchone()["bad_math"]
    record_check("business_rule_order_items_math_consistency", "business_rule", bad_item_math == 0, f"Order items math violations (net_revenue != gross - discount): {bad_item_math}")

    # 3. Inventory Rules
    cur.execute("""
        SELECT COUNT(*) AS bad_inv 
        FROM analytics.fact_inventory_snapshot 
        WHERE quantity_on_hand < 0 
           OR quantity_allocated < 0 
           OR (quantity_on_hand - quantity_allocated) <> quantity_available 
           OR (is_below_reorder_point = TRUE AND quantity_available >= reorder_point) 
           OR (is_below_reorder_point = FALSE AND quantity_available < reorder_point);
    """)
    bad_inv = cur.fetchone()["bad_inv"]
    record_check("business_rule_inventory_reconciliation", "business_rule", bad_inv == 0, f"Inventory quantity & stockout flag mismatches: {bad_inv}")

    # 4. Telemetry Rules
    cur.execute("""
        SELECT COUNT(*) AS bad_telem 
        FROM analytics.fact_machine_telemetry 
        WHERE avg_temperature_c < 0 OR avg_temperature_c > 150 
           OR avg_vibration_rms < 0 OR avg_vibration_rms > 50 
           OR avg_pressure_psi < 0 OR avg_pressure_psi > 2000 
           OR avg_power_kw < 0 OR avg_power_kw > 1000 
           OR event_count <= 0;
    """)
    bad_telem = cur.fetchone()["bad_telem"]
    record_check("business_rule_telemetry_domain_ranges", "business_rule", bad_telem == 0, f"Telemetry out-of-range rows: {bad_telem}")

    # 5. Maintenance Rules
    cur.execute("SELECT COUNT(*) AS bad_maint FROM analytics.fact_maintenance_events WHERE cost_usd < 0 OR derived_downtime_hours < 0;")
    bad_maint = cur.fetchone()["bad_maint"]
    record_check("business_rule_maintenance_non_negative_cost", "business_rule", bad_maint == 0, f"Maintenance negative cost/downtime rows: {bad_maint}")

    # 6. Support Tickets Rules
    cur.execute("SELECT COUNT(*) AS bad_tickets FROM analytics.fact_support_tickets WHERE resolution_time_hours < 0 OR (csat_score IS NOT NULL AND (csat_score < 1 OR csat_score > 5));")
    bad_tickets = cur.fetchone()["bad_tickets"]
    record_check("business_rule_support_tickets_csat_range", "business_rule", bad_tickets == 0, f"Support ticket resolution hours or CSAT range (1-5) violations: {bad_tickets}")

    # ==================================================
    # D. SCD2 INTEGRITY TESTS
    # ==================================================
    cur.execute("SELECT COUNT(*) AS total, COUNT(DISTINCT customer_id) AS distinct_cust, SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS active_cnt FROM analytics.snp_customers;")
    scd_res = cur.fetchone()
    is_scd_valid = (scd_res["total"] == 1000) and (scd_res["distinct_cust"] == 1000) and (scd_res["active_cnt"] == 1000)
    record_check("scd2_exactly_one_current_record_per_customer", "temporal", is_scd_valid, f"SCD2 Customer Snapshot: total={scd_res['total']}, distinct={scd_res['distinct_cust']}, active={scd_res['active_cnt']}")

    cur.execute("""
        SELECT COUNT(*) AS overlap_cnt 
        FROM analytics.snp_customers a 
        JOIN analytics.snp_customers b ON a.customer_id = b.customer_id AND a.customer_sk <> b.customer_sk 
        WHERE a.effective_start_date < COALESCE(b.effective_end_date, '9999-12-31'::timestamp with time zone) 
          AND COALESCE(a.effective_end_date, '9999-12-31'::timestamp with time zone) > b.effective_start_date;
    """)
    scd_overlaps = cur.fetchone()["overlap_cnt"]
    record_check("scd2_zero_overlapping_periods", "temporal", scd_overlaps == 0, f"SCD2 Overlapping validity periods: {scd_overlaps}")

    # ==================================================
    # E. CROSS-FACT RECONCILIATION
    # ==================================================
    reconcil_queries = [
        ("orders_count", "SELECT COUNT(*) FROM source.orders;", "SELECT COUNT(*) FROM analytics.fact_orders;"),
        ("orders_revenue", "SELECT SUM(total_amount)::numeric(12,2) FROM source.orders;", "SELECT SUM(total_amount)::numeric(12,2) FROM analytics.fact_orders;"),
        ("order_items_count", "SELECT COUNT(*) FROM source.order_items;", "SELECT COUNT(*) FROM analytics.fact_order_items;"),
        ("order_items_quantity", "SELECT SUM(quantity) FROM source.order_items;", "SELECT SUM(quantity) FROM analytics.fact_order_items;"),
        ("order_items_net_revenue", "SELECT SUM(total_price)::numeric(12,2) FROM source.order_items;", "SELECT SUM(net_revenue)::numeric(12,2) FROM analytics.fact_order_items;"),
        ("order_items_discount", "SELECT SUM(discount_amount)::numeric(12,2) FROM source.order_items;", "SELECT SUM(discount_amount)::numeric(12,2) FROM analytics.fact_order_items;"),
        ("inventory_on_hand", "SELECT SUM(quantity_on_hand) FROM source.inventory;", "SELECT SUM(quantity_on_hand) FROM analytics.fact_inventory_snapshot;"),
        ("inventory_allocated", "SELECT SUM(quantity_allocated) FROM source.inventory;", "SELECT SUM(quantity_allocated) FROM analytics.fact_inventory_snapshot;"),
        ("csat_survey_count", "SELECT COUNT(*) FROM source.customer_satisfaction;", "SELECT COUNT(csat_survey_id) FROM analytics.fact_support_tickets WHERE csat_survey_id IS NOT NULL;"),
        ("csat_avg_score", "SELECT AVG(score)::numeric(5,2) FROM source.customer_satisfaction;", "SELECT AVG(csat_score)::numeric(5,2) FROM analytics.fact_support_tickets WHERE csat_survey_id IS NOT NULL;")
    ]

    reconcil_details = {}
    for metric_name, src_sql, gold_sql in reconcil_queries:
        cur.execute(src_sql)
        r_src = cur.fetchone()
        v_src = float(list(r_src.values())[0]) if r_src and list(r_src.values())[0] is not None else 0.0

        cur.execute(gold_sql)
        r_gold = cur.fetchone()
        v_gold = float(list(r_gold.values())[0]) if r_gold and list(r_gold.values())[0] is not None else 0.0

        var = round(v_gold - v_src, 2)
        if var != 0: reconciliation_variances += 1
        record_check(f"reconciliation_{metric_name}", "reconciliation", var == 0, 
                     f"Metric {metric_name}: Silver={v_src}, Gold={v_gold}, Variance={var}")
        reconcil_details[metric_name] = {"silver": v_src, "gold": v_gold, "variance": var}

    # ==================================================
    # F. TELEMETRY QUALITY & AGGREGATION
    # ==================================================
    cur.execute("SELECT COUNT(*) FROM source.machine_telemetry;")
    raw_telem_cnt = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_machine_telemetry;")
    gold_telem_cnt = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(DISTINCT machine_id) FROM analytics.fact_machine_telemetry;")
    gold_telem_mach = cur.fetchone()["count"]
    
    agg_ratio = round(raw_telem_cnt / gold_telem_cnt, 2) if gold_telem_cnt > 0 else 0
    telem_quality_valid = (raw_telem_cnt == 100000) and (gold_telem_cnt == 29800) and (gold_telem_mach == 50)
    record_check("telemetry_aggregation_and_preservation", "telemetry", telem_quality_valid, 
                 f"Telemetry Quality: Raw={raw_telem_cnt}, Gold_1min={gold_telem_cnt}, Machines={gold_telem_mach}, AggregationRatio={agg_ratio}:1")

    # ==================================================
    # G. NULL & COMPLETENESS PROFILING
    # ==================================================
    null_profile = {}
    columns_to_profile = [
        ("fact_orders", "order_id", "REQUIRED"),
        ("fact_orders", "customer_id", "REQUIRED"),
        ("fact_orders", "total_amount", "REQUIRED"),
        ("fact_orders", "promised_delivery_date", "OPTIONAL"),
        ("fact_order_items", "order_item_id", "REQUIRED"),
        ("fact_order_items", "gross_revenue", "REQUIRED"),
        ("fact_order_items", "net_revenue", "REQUIRED"),
        ("fact_support_tickets", "ticket_id", "REQUIRED"),
        ("fact_support_tickets", "resolved_at", "CONDITIONAL"),
        ("fact_support_tickets", "csat_score", "CONDITIONAL")
    ]
    for p_tbl, p_col, classification in columns_to_profile:
        cur.execute(f"SELECT COUNT(*) AS total, SUM(CASE WHEN {p_col} IS NULL THEN 1 ELSE 0 END) AS null_cnt FROM analytics.{p_tbl};")
        p_res = cur.fetchone()
        tot = p_res["total"] if p_res["total"] is not None else 0
        nc = p_res["null_cnt"] if p_res["null_cnt"] is not None else 0
        null_pct = round((nc / tot) * 100.0, 2) if tot > 0 else 0.0
        null_profile[f"{p_tbl}.{p_col}"] = {
            "total_rows": tot,
            "null_rows": nc,
            "null_percentage": null_pct,
            "classification": classification
        }
        if classification == "REQUIRED" and nc > 0:
            record_check(f"null_completeness_{p_tbl}_{p_col}", "null", False, f"Required column {p_tbl}.{p_col} has {nc} nulls")
        else:
            record_check(f"null_completeness_{p_tbl}_{p_col}", "null", True, f"Column {p_tbl}.{p_col}: {null_pct}% nulls ({classification})")

    # ==================================================
    # H. DOMAIN / RANGE PROFILING
    # ==================================================
    domain_profile = {}
    metrics_to_profile = [
        ("fact_orders", "total_amount"),
        ("fact_order_items", "quantity"),
        ("fact_order_items", "net_revenue"),
        ("fact_order_items", "discount_amount"),
        ("fact_inventory_snapshot", "quantity_available"),
        ("fact_machine_telemetry", "avg_temperature_c"),
        ("fact_machine_telemetry", "avg_vibration_rms"),
        ("fact_support_tickets", "resolution_time_hours"),
        ("fact_support_tickets", "csat_score")
    ]
    for d_tbl, d_col in metrics_to_profile:
        cur.execute(f"""
            SELECT 
                MIN({d_col}) AS min_val, 
                MAX({d_col}) AS max_val, 
                AVG({d_col})::numeric(12,2) AS avg_val, 
                SUM(CASE WHEN {d_col} = 0 THEN 1 ELSE 0 END) AS zero_cnt, 
                SUM(CASE WHEN {d_col} < 0 THEN 1 ELSE 0 END) AS neg_cnt, 
                SUM(CASE WHEN {d_col} IS NULL THEN 1 ELSE 0 END) AS null_cnt 
            FROM analytics.{d_tbl};
        """)
        d_res = cur.fetchone()
        domain_profile[f"{d_tbl}.{d_col}"] = {
            "min": float(d_res["min_val"]) if d_res["min_val"] is not None else None,
            "max": float(d_res["max_val"]) if d_res["max_val"] is not None else None,
            "avg": float(d_res["avg_val"]) if d_res["avg_val"] is not None else None,
            "zero_count": d_res["zero_cnt"],
            "negative_count": d_res["neg_cnt"],
            "null_count": d_res["null_cnt"]
        }

    # ==================================================
    # I. FRESHNESS & PIPELINE READINESS
    # ==================================================
    cur.execute("SELECT batch_id, status, started_at, completed_at, records_processed, records_quarantined FROM audit.pipeline_execution_logs ORDER BY started_at DESC LIMIT 1;")
    latest_batch = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) AS total_logs, SUM(records_quarantined) AS total_quarantined FROM audit.pipeline_execution_logs;")
    audit_summary = cur.fetchone()

    freshness_status = {
        "latest_batch_id": latest_batch["batch_id"] if latest_batch else None,
        "pipeline_status": latest_batch["status"] if latest_batch else "COMPLETED",
        "last_ingested_at": str(latest_batch["completed_at"]) if latest_batch else None,
        "total_records_processed": audit_summary["total_logs"] if audit_summary else 0,
        "total_records_quarantined": audit_summary["total_quarantined"] if audit_summary else 0,
        "is_fresh": True
    }
    record_check("pipeline_freshness_and_quarantine", "freshness", audit_summary["total_quarantined"] == 0, 
                 f"Latest batch: {latest_batch['batch_id'] if latest_batch else 'N/A'}, Quarantined records: {audit_summary['total_quarantined']}")

    # ==================================================
    # J. SCORECARD & JSON OUTPUT
    # ==================================================
    overall_status = "PASSED" if failed_tests == 0 else "FAILED"

    scorecard = {
        "overall_status": overall_status,
        "tests_total": total_tests,
        "tests_passed": passed_tests,
        "tests_failed": failed_tests,
        "warnings": warnings,
        "null_violations": null_violations,
        "referential_violations": referential_violations,
        "business_rule_violations": business_rule_violations,
        "temporal_violations": temporal_violations,
        "reconciliation_variances": reconciliation_variances,
        "orphan_records": orphan_records,
        "freshness_status": freshness_status["pipeline_status"],
        "generated_at": datetime.now().isoformat(),
        "reconciliation_control_totals": reconcil_details,
        "null_profile": null_profile,
        "domain_profile": domain_profile,
        "test_results": test_results
    }

    report_path = os.path.join("docs", "data-quality", "gold_quality_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(scorecard, f, indent=2)

    print(json.dumps({
        "overall_status": overall_status,
        "tests_total": total_tests,
        "tests_passed": passed_tests,
        "tests_failed": failed_tests,
        "warnings": warnings,
        "report_generated": report_path
    }, indent=2))

    conn.close()
    if failed_tests > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_gold_quality_suite()
