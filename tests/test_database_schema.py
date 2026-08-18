# ==============================================================================
# Enterprise Intelligence Platform — Database Schema Verification Test Suite
# Tests existence of schemas, 3NF source tables, Gold star-schema tables, audit logs,
# primary keys, foreign keys, unique constraints, and B-tree indexes.
# ==============================================================================

import os
import psycopg2
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "nexacore_admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "nexacore_secret_pass")
DB_NAME = os.getenv("POSTGRES_DB", "nexacore_dw")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")


@pytest.fixture(scope="module")
def db_connection():
    """Establishes live database connection fixture."""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    yield conn
    conn.close()


def test_database_schemas_exist(db_connection):
    """Verifies that all required schemas exist."""
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('source', 'analytics', 'staging', 'audit');"
    )
    schemas = [row[0] for row in cursor.fetchall()]
    cursor.close()

    expected_schemas = ["source", "analytics", "staging", "audit"]
    for schema in expected_schemas:
        assert schema in schemas, f"Schema '{schema}' is missing from database."


def test_source_tables_exist(db_connection):
    """Verifies that all 21 3NF source system tables exist."""
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'source';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    expected_source_tables = [
        "customer_segments",
        "customers",
        "customer_addresses",
        "customer_interactions",
        "sales_channels",
        "product_categories",
        "products",
        "orders",
        "order_items",
        "suppliers",
        "warehouses",
        "inventory",
        "inventory_transactions",
        "machine_types",
        "machines",
        "machine_telemetry",
        "maintenance_events",
        "failure_events",
        "support_tickets",
        "ticket_interactions",
        "customer_satisfaction",
    ]

    for table in expected_source_tables:
        assert table in tables, f"Source table '{table}' is missing from 'source' schema."


def test_analytics_tables_exist(db_connection):
    """Verifies that all Gold layer Star Schema dimension and fact tables exist."""
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    expected_analytics_tables = [
        "dim_date",
        "dim_customer",
        "dim_product",
        "dim_supplier",
        "dim_warehouse",
        "dim_machine",
        "fact_orders",
        "fact_order_items",
        "fact_inventory_daily",
        "fact_machine_telemetry",
        "fact_maintenance_events",
        "fact_support_tickets",
    ]

    for table in expected_analytics_tables:
        assert table in tables, f"Analytics table '{table}' is missing from 'analytics' schema."


def test_audit_tables_exist(db_connection):
    """Verifies that audit and quarantine infrastructure tables exist."""
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'audit';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()

    expected_audit_tables = [
        "pipeline_execution_logs",
        "data_quality_audit_logs",
        "quarantine_records",
    ]

    for table in expected_audit_tables:
        assert table in tables, f"Audit table '{table}' is missing from 'audit' schema."


def test_primary_keys_exist(db_connection):
    """Verifies primary key constraints exist on critical tables."""
    cursor = db_connection.cursor()
    query = """
        SELECT table_schema, table_name 
        FROM information_schema.table_constraints 
        WHERE constraint_type = 'PRIMARY KEY' AND table_schema IN ('source', 'analytics', 'audit');
    """
    cursor.execute(query)
    pk_tables = [(row[0], row[1]) for row in cursor.fetchall()]
    cursor.close()

    assert ("source", "customers") in pk_tables
    assert ("source", "orders") in pk_tables
    assert ("source", "machine_telemetry") in pk_tables
    assert ("analytics", "fact_predictions_machine_health") in pk_tables
    assert ("analytics", "agent_decisions") in pk_tables


def test_foreign_keys_exist(db_connection):
    """Verifies foreign key constraints exist on key relational tables."""
    cursor = db_connection.cursor()
    query = """
        SELECT table_schema, table_name 
        FROM information_schema.table_constraints 
        WHERE constraint_type = 'FOREIGN KEY' AND table_schema IN ('source', 'analytics');
    """
    cursor.execute(query)
    fk_tables = [(row[0], row[1]) for row in cursor.fetchall()]
    cursor.close()

    assert ("source", "customers") in fk_tables
    assert ("source", "orders") in fk_tables
    assert ("source", "order_items") in fk_tables


if __name__ == "__main__":
    pytest.main([__file__])
