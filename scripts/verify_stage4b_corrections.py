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

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Machine count
    cur.execute("SELECT COUNT(*) AS machine_count FROM source.machines;")
    machine_count = cur.fetchone()["machine_count"]
    
    # 2. Supplier relationships check
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='source' AND table_name='products';")
    product_cols = [r["column_name"] for r in cur.fetchall()]
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='source' AND table_name='inventory';")
    inventory_cols = [r["column_name"] for r in cur.fetchall()]

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='source' AND table_name='suppliers';")
    supplier_cols = [r["column_name"] for r in cur.fetchall()]

    # Foreign keys in source schema
    cur.execute("""
        SELECT
            tc.table_name, kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='source';
    """)
    foreign_keys = cur.fetchall()

    # 3. Inventory temporal coverage
    cur.execute("""
        SELECT 
            MIN(last_count_date) AS min_count_date, 
            MAX(last_count_date) AS max_count_date,
            COUNT(DISTINCT last_count_date) AS distinct_dates,
            COUNT(*) AS total_inventory_records
        FROM source.inventory;
    """)
    inventory_stats = cur.fetchone()

    # 4. Order columns
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='source' AND table_name='orders';")
    order_cols = cur.fetchall()

    result = {
        "machine_count": machine_count,
        "product_cols": product_cols,
        "inventory_cols": inventory_cols,
        "supplier_cols": supplier_cols,
        "has_supplier_in_products": "supplier_id" in product_cols,
        "has_supplier_in_inventory": "supplier_id" in inventory_cols,
        "foreign_keys": [dict(fk) for fk in foreign_keys],
        "inventory_stats": {
            "min_count_date": str(inventory_stats["min_count_date"]),
            "max_count_date": str(inventory_stats["max_count_date"]),
            "distinct_dates": inventory_stats["distinct_dates"],
            "total_inventory_records": inventory_stats["total_inventory_records"],
        },
        "order_cols": [dict(c) for c in order_cols],
        "has_actual_delivery_date": any(c["column_name"] == "actual_delivery_date" for c in order_cols)
    }

    print(json.dumps(result, indent=2))
    conn.close()

if __name__ == "__main__":
    main()
