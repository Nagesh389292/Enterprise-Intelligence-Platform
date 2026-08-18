import psycopg2
import subprocess
import sys
import os

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

def reset_and_rebuild():
    print("==================================================")
    print("STEP 1: Resetting Ingestion Checkpoints & Source Tables")
    print("==================================================")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("ALTER TABLE source.customers DROP CONSTRAINT IF EXISTS customers_contact_email_key;")
    cur.execute("TRUNCATE audit.pipeline_execution_logs CASCADE;")
    
    tables = [
        "customer_segments", "product_categories", "sales_channels", "machine_types", "suppliers", "warehouses",
        "customers", "products", "machines", "customer_addresses", "orders", "order_items", "inventory",
        "machine_telemetry", "maintenance_events", "failure_events", "support_tickets", "customer_satisfaction"
    ]
    for t in tables:
        cur.execute(f"TRUNCATE source.{t} CASCADE;")
    cur.execute("""
        INSERT INTO source.sales_channels (channel_id, channel_code, channel_name, commission_rate) VALUES
        (1, 'DIRECT', 'Direct Enterprise Sales', 0.0500),
        (2, 'PARTNER', 'Partner Channel Network', 0.1000),
        (3, 'ONLINE', 'Digital Self-Service Portal', 0.0200)
        ON CONFLICT (channel_id) DO NOTHING;
    """)
    conn.commit()
    conn.close()
    print("Audit logs and source tables reset cleanly, sales_channels seeded.")

    print("\n==================================================")
    print("STEP 2: Executing Clean Ingestion (--force)")
    print("==================================================")
    ingest_cmd = [sys.executable, "-m", "scripts.ingestion.cli", "ingest", "--force"]
    res = subprocess.run(ingest_cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("Ingestion FAILED:", res.stderr)
        sys.exit(1)

    print("\n==================================================")
    print("STEP 3: Executing dbt build")
    print("==================================================")
    dbt_exe = os.path.join(sys.prefix, "Scripts", "dbt.exe") if os.name == "nt" else "dbt"
    dbt_cmd = [dbt_exe, "build", "--profiles-dir", "."]
    res_dbt = subprocess.run(dbt_cmd, cwd="dbt", capture_output=True, text=True)
    print(res_dbt.stdout)
    if res_dbt.returncode != 0:
        print("dbt build FAILED:", res_dbt.stderr)
        sys.exit(1)

    print("\n==================================================")
    print("STEP 4: Executing Gold Data Quality Suite")
    print("==================================================")
    qual_cmd = [sys.executable, "scripts/gold_quality_suite.py"]
    res_qual = subprocess.run(qual_cmd, capture_output=True, text=True)
    print(res_qual.stdout)

if __name__ == "__main__":
    reset_and_rebuild()
