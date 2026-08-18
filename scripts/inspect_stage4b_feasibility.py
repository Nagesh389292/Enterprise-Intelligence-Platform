"""
Stage 4B Pre-Flight Data Profiling & Feasibility Inspection Script.
Inspects live PostgreSQL source.* schema and data on port 5433 to verify Gold analytical model feasibility.
Does NOT perform any database mutations or schema modifications.
"""

import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_inspection():
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    user = os.getenv("POSTGRES_USER", "nexacore_admin")
    password = os.getenv("POSTGRES_PASSWORD", "nexacore_secret_pass")
    dbname = os.getenv("POSTGRES_DB", "nexacore_dw")
    
    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cursor = conn.cursor()
    
    report = {}
    
    # 1. Source Table & Column Metadata Inspection
    cursor.execute("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'source'
        ORDER BY table_name, ordinal_position;
    """)
    tables_meta = {}
    for tbl, col, dtype, nullable in cursor.fetchall():
        if tbl not in tables_meta:
            tables_meta[tbl] = []
        tables_meta[tbl].append({"column": col, "data_type": dtype, "nullable": nullable})
    report["source_tables_metadata"] = tables_meta
    
    # 2. Row Counts and Baseline Reconciliations
    tables = [
        "customer_segments", "customers", "customer_addresses", "customer_interactions",
        "sales_channels", "product_categories", "products", "orders", "order_items",
        "suppliers", "warehouses", "inventory", "inventory_transactions",
        "machine_types", "machines", "machine_telemetry", "maintenance_events",
        "failure_events", "support_tickets", "ticket_interactions", "customer_satisfaction"
    ]
    counts = {}
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM source.{t};")
        counts[t] = cursor.fetchone()[0]
    report["row_counts"] = counts
    
    # 3. Date Ranges & Temporal Bounds
    date_bounds = {}
    date_queries = {
        "orders": "SELECT MIN(order_timestamp), MAX(order_timestamp) FROM source.orders;",
        "machine_telemetry": "SELECT MIN(recorded_at), MAX(recorded_at) FROM source.machine_telemetry;",
        "maintenance_events": "SELECT MIN(performed_at), MAX(performed_at) FROM source.maintenance_events;",
        "failure_events": "SELECT MIN(occurred_at), MAX(occurred_at) FROM source.failure_events;",
        "support_tickets": "SELECT MIN(created_at), MAX(created_at) FROM source.support_tickets;",
        "customer_satisfaction": "SELECT MIN(submitted_at), MAX(submitted_at) FROM source.customer_satisfaction;"
    }
    for key, q in date_queries.items():
        cursor.execute(q)
        min_d, max_d = cursor.fetchone()
        date_bounds[key] = {"min_date": str(min_d), "max_date": str(max_d)}
    report["date_bounds"] = date_bounds
    
    # 4. Metric Baseline Totals
    cursor.execute("SELECT SUM(total_amount), AVG(total_amount) FROM source.orders;")
    tot_amt, avg_amt = cursor.fetchone()
    
    cursor.execute("SELECT SUM(quantity), SUM(total_price), SUM(discount_amount) FROM source.order_items;")
    tot_qty, tot_rev, tot_disc = cursor.fetchone()
    
    cursor.execute("SELECT SUM(quantity_on_hand), SUM(quantity_allocated) FROM source.inventory;")
    tot_on_hand, tot_alloc = cursor.fetchone()
    
    cursor.execute("SELECT AVG(temperature_c), MAX(temperature_c), AVG(vibration_rms), MAX(vibration_rms) FROM source.machine_telemetry;")
    avg_t, max_t, avg_v, max_v = cursor.fetchone()
    
    cursor.execute("SELECT AVG(score), COUNT(*) FROM source.customer_satisfaction;")
    avg_csat, cnt_csat = cursor.fetchone()
    
    report["baseline_metrics"] = {
        "orders_sum_total_amount": float(tot_amt) if tot_amt else 0.0,
        "orders_avg_total_amount": float(avg_amt) if avg_amt else 0.0,
        "order_items_sum_quantity": int(tot_qty) if tot_qty else 0,
        "order_items_sum_total_price": float(tot_rev) if tot_rev else 0.0,
        "order_items_sum_discount": float(tot_disc) if tot_disc else 0.0,
        "inventory_sum_on_hand": int(tot_on_hand) if tot_on_hand else 0,
        "inventory_sum_allocated": int(tot_alloc) if tot_alloc else 0,
        "telemetry_avg_temp": float(avg_t) if avg_t else 0.0,
        "telemetry_max_temp": float(max_t) if max_t else 0.0,
        "telemetry_avg_vibration": float(avg_v) if avg_v else 0.0,
        "telemetry_max_vibration": float(max_v) if max_v else 0.0,
        "csat_avg_score": float(avg_csat) if avg_csat else 0.0,
        "csat_total_surveys": int(cnt_csat)
    }
    
    # 5. SCD Type 2 Column Check in Customers and Machines
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'source' AND table_name = 'customers';")
    cust_cols = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'source' AND table_name = 'machines';")
    mach_cols = [r[0] for r in cursor.fetchall()]
    
    report["scd2_feasibility"] = {
        "customers_has_updated_at": "updated_at" in cust_cols,
        "customers_has_history_log": False,
        "machines_has_updated_at": "updated_at" in mach_cols,
        "machines_has_history_log": False
    }
    
    conn.close()
    
    print(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    run_inspection()
