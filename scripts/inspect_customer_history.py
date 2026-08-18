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

def inspect_customer_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Total customer count vs distinct customer_id
    cur.execute("SELECT COUNT(*) AS total, COUNT(DISTINCT customer_id) AS distinct_cust FROM source.customers;")
    cust_counts = cur.fetchone()
    
    # 2. Check for updated_at column or historical tables
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'source' AND table_name = 'customers';
    """)
    cols = cur.fetchall()
    
    # 3. Check customer addresses count per customer
    cur.execute("""
        SELECT customer_id, COUNT(*) as addr_count 
        FROM source.customer_addresses 
        GROUP BY customer_id 
        HAVING COUNT(*) > 1;
    """)
    multi_addr = cur.fetchall()

    results = {
        "total_customer_rows": cust_counts["total"],
        "distinct_customer_ids": cust_counts["distinct_cust"],
        "has_historical_versions": cust_counts["total"] > cust_counts["distinct_cust"],
        "customer_columns": [c["column_name"] for c in cols],
        "customers_with_multiple_addresses": len(multi_addr)
    }

    print(json.dumps(results, indent=2))
    conn.close()

if __name__ == "__main__":
    inspect_customer_data()
