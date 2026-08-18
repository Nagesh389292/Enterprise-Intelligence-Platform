import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

def reconcile_scd2():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Source Customer Count vs SCD2 Row Count
    cur.execute("SELECT COUNT(*) FROM source.customers;")
    source_cust_count = cur.fetchone()["count"]
    
    cur.execute("SELECT COUNT(*) FROM analytics.snp_customers;")
    scd2_row_count = cur.fetchone()["count"]
    
    cur.execute("SELECT COUNT(DISTINCT customer_id) FROM analytics.snp_customers;")
    distinct_cust_count = cur.fetchone()["count"]

    # 2. Historical Version Metrics
    cur.execute("SELECT COUNT(*) FROM analytics.snp_customers WHERE record_version > 1;")
    historical_version_count = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.snp_customers WHERE is_current = true;")
    current_record_count = cur.fetchone()["count"]

    cur.execute("""
        SELECT customer_id, COUNT(*) 
        FROM analytics.snp_customers 
        GROUP BY customer_id 
        HAVING COUNT(*) > 1;
    """)
    custs_with_multi_versions = cur.fetchall()

    cur.execute("""
        SELECT customer_id 
        FROM analytics.snp_customers 
        GROUP BY customer_id 
        HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) = 0;
    """)
    custs_with_zero_current = cur.fetchall()

    cur.execute("""
        SELECT customer_id 
        FROM analytics.snp_customers 
        GROUP BY customer_id 
        HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) > 1;
    """)
    custs_with_multi_current = cur.fetchall()

    # 3. Temporal Overlap Validation
    cur.execute("""
        SELECT a.customer_id
        FROM analytics.snp_customers a
        JOIN analytics.snp_customers b 
          ON a.customer_id = b.customer_id 
         AND a.customer_sk <> b.customer_sk
        WHERE a.effective_start_date < COALESCE(b.effective_end_date, '9999-12-31'::timestamp with time zone)
          AND COALESCE(a.effective_end_date, '9999-12-31'::timestamp with time zone) > b.effective_start_date;
    """)
    overlapping_periods = cur.fetchall()

    # 4. Orphan Customer References Check across Orders and Support Tickets
    cur.execute("""
        SELECT COUNT(*) 
        FROM analytics.fact_orders o 
        LEFT JOIN analytics.snp_customers c ON o.customer_id = c.customer_id 
        WHERE c.customer_id IS NULL;
    """)
    orphan_orders_scd2 = cur.fetchone()["count"]

    cur.execute("""
        SELECT COUNT(*) 
        FROM analytics.fact_support_tickets t 
        LEFT JOIN analytics.snp_customers c ON t.customer_id = c.customer_id 
        WHERE c.customer_id IS NULL;
    """)
    orphan_tickets_scd2 = cur.fetchone()["count"]

    results = {
        "scd2_reconciliation": {
            "source_customer_count": source_cust_count,
            "scd2_physical_row_count": scd2_row_count,
            "distinct_customer_id_count": distinct_cust_count,
            "historical_version_count": historical_version_count,
            "current_record_count": current_record_count,
            "customers_with_multi_versions": len(custs_with_multi_versions),
            "customers_with_zero_current": len(custs_with_zero_current),
            "customers_with_multi_current": len(custs_with_multi_current),
            "overlapping_periods_count": len(overlapping_periods),
            "genuine_historical_changes_exist": False,
            "limitation_note": "Source database provides a snapshot dataset (1 version per customer). SCD2 table structure is created with Version 1 open-ended current records without fabricating artificial historical changes."
        },
        "orphan_checks": {
            "orphan_orders_scd2_customers": orphan_orders_scd2,
            "orphan_tickets_scd2_customers": orphan_tickets_scd2,
            "has_orphans": orphan_orders_scd2 > 0 or orphan_tickets_scd2 > 0
        }
    }

    print(json.dumps(results, indent=2))
    conn.close()

if __name__ == "__main__":
    reconcile_scd2()
