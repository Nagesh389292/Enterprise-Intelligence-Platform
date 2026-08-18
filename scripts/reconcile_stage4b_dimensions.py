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
    
    # 1. Compare row counts between source.* and analytics.* dimensions
    dim_queries = {
        "dim_customer": ("SELECT COUNT(*) FROM source.customers;", "SELECT COUNT(*) FROM analytics.dim_customer;"),
        "dim_product": ("SELECT COUNT(*) FROM source.products;", "SELECT COUNT(*) FROM analytics.dim_product;"),
        "dim_supplier": ("SELECT COUNT(*) FROM source.suppliers;", "SELECT COUNT(*) FROM analytics.dim_supplier;"),
        "dim_warehouse": ("SELECT COUNT(*) FROM source.warehouses;", "SELECT COUNT(*) FROM analytics.dim_warehouse;"),
        "dim_machine": ("SELECT COUNT(*) FROM source.machines;", "SELECT COUNT(*) FROM analytics.dim_machine;"),
        "dim_date": ("SELECT 1095;", "SELECT COUNT(*) FROM analytics.dim_date;"),
    }
    
    reconciliation_results = {}
    for dim, (source_sql, dim_sql) in dim_queries.items():
        cur.execute(source_sql)
        src_cnt = list(cur.fetchone().values())[0]
        cur.execute(dim_sql)
        dim_cnt = list(cur.fetchone().values())[0]
        reconciliation_results[dim] = {
            "source_count": src_cnt,
            "gold_dim_count": dim_cnt,
            "variance": dim_cnt - src_cnt,
            "reconciled": dim_cnt == src_cnt
        }

    # 2. Check for orphan keys
    # Check if dim_customer.segment_id exists in source.customer_segments
    cur.execute("""
        SELECT COUNT(*) AS orphan_count
        FROM analytics.dim_customer c
        LEFT JOIN source.customer_segments s ON c.segment_id = s.segment_id
        WHERE s.segment_id IS NULL AND c.segment_id IS NOT NULL;
    """)
    orphan_customer_segments = cur.fetchone()["orphan_count"]

    # Check if dim_product.category_id exists in source.product_categories
    cur.execute("""
        SELECT COUNT(*) AS orphan_count
        FROM analytics.dim_product p
        LEFT JOIN source.product_categories c ON p.category_id = c.category_id
        WHERE c.category_id IS NULL AND p.category_id IS NOT NULL;
    """)
    orphan_product_categories = cur.fetchone()["orphan_count"]

    # Check if dim_machine.machine_type_id exists in source.machine_types
    cur.execute("""
        SELECT COUNT(*) AS orphan_count
        FROM analytics.dim_machine m
        LEFT JOIN source.machine_types mt ON m.machine_type_id = mt.machine_type_id
        WHERE mt.machine_type_id IS NULL AND m.machine_type_id IS NOT NULL;
    """)
    orphan_machine_types = cur.fetchone()["orphan_count"]

    # Check if dim_machine.warehouse_id exists in source.warehouses
    cur.execute("""
        SELECT COUNT(*) AS orphan_count
        FROM analytics.dim_machine m
        LEFT JOIN source.warehouses w ON m.warehouse_id = w.warehouse_id
        WHERE w.warehouse_id IS NULL AND m.warehouse_id IS NOT NULL;
    """)
    orphan_machine_warehouses = cur.fetchone()["orphan_count"]

    output = {
        "reconciliation": reconciliation_results,
        "orphan_checks": {
            "orphan_customer_segments": orphan_customer_segments,
            "orphan_product_categories": orphan_product_categories,
            "orphan_machine_types": orphan_machine_types,
            "orphan_machine_warehouses": orphan_machine_warehouses,
            "has_orphans": any([
                orphan_customer_segments > 0,
                orphan_product_categories > 0,
                orphan_machine_types > 0,
                orphan_machine_warehouses > 0
            ])
        }
    }

    print(json.dumps(output, indent=2))
    conn.close()

if __name__ == "__main__":
    main()
