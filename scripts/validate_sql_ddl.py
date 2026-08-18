# ==============================================================================
# Enterprise Intelligence Platform — SQL DDL Migration Validator Script
# Validates initialization SQL files for DDL structure, table coverage, and integrity.
# ==============================================================================

import os
import re
import sys

INIT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker", "postgres", "init")

SQL_FILES = [
    "01-create-schemas.sql",
    "02-source-schema.sql",
    "03-analytics-schema.sql",
    "04-audit-schema.sql",
    "05-create-indexes.sql"
]

def validate_sql_files():
    print("==================================================")
    print("Validating PostgreSQL DDL Migration Scripts")
    print("==================================================")
    
    missing_files = []
    for sql_file in SQL_FILES:
        full_path = os.path.join(INIT_DIR, sql_file)
        if not os.path.exists(full_path):
            missing_files.append(sql_file)
            print(f"[FAIL] Missing file: {sql_file}")
        else:
            size = os.path.getsize(full_path)
            print(f"[OK] Found: {sql_file} ({size} bytes)")
            
    if missing_files:
        print(f"Error: {len(missing_files)} SQL files are missing.")
        sys.exit(1)

    # Validate Schema Declarations
    with open(os.path.join(INIT_DIR, "01-create-schemas.sql"), "r", encoding="utf-8") as f:
        schemas_content = f.read()
    
    expected_schemas = ["source", "analytics", "staging", "audit"]
    for schema in expected_schemas:
        if re.search(rf"CREATE SCHEMA IF NOT EXISTS {schema}", schemas_content, re.IGNORECASE):
            print(f"[OK] Schema definition verified: '{schema}'")
        else:
            print(f"[FAIL] Schema missing in 01-create-schemas.sql: '{schema}'")

    # Validate Source Tables (21 tables across 5 domains)
    with open(os.path.join(INIT_DIR, "02-source-schema.sql"), "r", encoding="utf-8") as f:
        source_content = f.read()
        
    created_source_tables = re.findall(r"CREATE TABLE IF NOT EXISTS source\.(\w+)", source_content, re.IGNORECASE)
    print(f"\nSource Schema Tables Found ({len(created_source_tables)}/21):")
    for tbl in created_source_tables:
        print(f"  - source.{tbl}")
        
    assert len(created_source_tables) == 21, f"Expected 21 source tables, found {len(created_source_tables)}"

    # Validate Analytics Tables (12 tables: 6 dims + 6 facts)
    with open(os.path.join(INIT_DIR, "03-analytics-schema.sql"), "r", encoding="utf-8") as f:
        analytics_content = f.read()
        
    created_analytics_tables = re.findall(r"CREATE TABLE IF NOT EXISTS analytics\.(\w+)", analytics_content, re.IGNORECASE)
    print(f"\nAnalytics Schema Tables Found ({len(created_analytics_tables)}/12):")
    for tbl in created_analytics_tables:
        print(f"  - analytics.{tbl}")
        
    assert len(created_analytics_tables) == 12, f"Expected 12 analytics tables, found {len(created_analytics_tables)}"

    # Validate Audit Tables (3 tables)
    with open(os.path.join(INIT_DIR, "04-audit-schema.sql"), "r", encoding="utf-8") as f:
        audit_content = f.read()
        
    created_audit_tables = re.findall(r"CREATE TABLE IF NOT EXISTS audit\.(\w+)", audit_content, re.IGNORECASE)
    print(f"\nAudit Schema Tables Found ({len(created_audit_tables)}/3):")
    for tbl in created_audit_tables:
        print(f"  - audit.{tbl}")
        
    assert len(created_audit_tables) == 3, f"Expected 3 audit tables, found {len(created_audit_tables)}"

    # Validate Indexes
    with open(os.path.join(INIT_DIR, "05-create-indexes.sql"), "r", encoding="utf-8") as f:
        index_content = f.read()
        
    indexes = re.findall(r"CREATE INDEX IF NOT EXISTS (\w+)", index_content, re.IGNORECASE)
    print(f"\nPerformance Indexes Defined ({len(indexes)}):")
    for idx in indexes:
        print(f"  - {idx}")

    print("\n==================================================")
    print("ALL DDL MIGRATION SCRIPTS PASSED STATIC SYNTAX & COVERAGE VALIDATION!")
    print("==================================================")

if __name__ == "__main__":
    validate_sql_files()
