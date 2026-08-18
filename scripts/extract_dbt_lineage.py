"""
NexaCore Data Engineering Platform — Stage 4B Phase 8
dbt Lineage & Catalog Metadata Extraction Engine

Parses dbt/target/manifest.json and dbt/target/catalog.json to summarize:
1. Model & Source Catalog counts.
2. Layer-by-layer dependency DAG edges.
3. Column coverage and documentation metrics.
4. Output JSON summary: docs/governance/dbt_lineage_summary.json
"""

import os
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(PROJECT_ROOT, "dbt", "target", "manifest.json")
CATALOG_PATH = os.path.join(PROJECT_ROOT, "dbt", "target", "catalog.json")
OUTPUT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "governance", "dbt_lineage_summary.json")

def extract_lineage():
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"manifest.json not found at {MANIFEST_PATH}")
    if not os.path.exists(CATALOG_PATH):
        raise FileNotFoundError(f"catalog.json not found at {CATALOG_PATH}")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    nodes = manifest.get("nodes", {})
    sources = manifest.get("sources", {})

    models_by_layer = {
        "staging": [],
        "dimensions": [],
        "facts": [],
        "snapshots": [],
        "ml": []
    }

    edges = []
    total_columns = 0
    documented_columns = 0

    for node_id, node in nodes.items():
        if node.get("resource_type") == "model":
            name = node.get("name")
            schema = node.get("schema")
            materialized = node.get("config", {}).get("materialized")

            # Layer categorization
            if name.startswith("stg_"):
                layer = "staging"
            elif name.startswith("dim_"):
                layer = "dimensions"
            elif name.startswith("fact_"):
                layer = "facts"
            elif name.startswith("snp_"):
                layer = "snapshots"
            elif name.startswith("ml_"):
                layer = "ml"
            else:
                layer = "other"

            if layer in models_by_layer:
                models_by_layer[layer].append(name)

            # Dependencies
            depends_on = node.get("depends_on", {}).get("nodes", [])
            for parent in depends_on:
                parent_name = parent.split(".")[-1]
                edges.append({"from": parent_name, "to": name})

            # Column documentation metrics from catalog
            cat_node = catalog.get("nodes", {}).get(node_id, {})
            columns = cat_node.get("columns", {})
            manifest_cols = node.get("columns", {})
            
            for col_name in columns.keys():
                total_columns += 1
                col_desc = manifest_cols.get(col_name, {}).get("description", "")
                if col_desc and len(col_desc.strip()) > 0:
                    documented_columns += 1

    summary = {
        "status": "PASSED",
        "generated_at": manifest.get("metadata", {}).get("generated_at"),
        "dbt_version": manifest.get("metadata", {}).get("dbt_version"),
        "total_sources": len(sources),
        "total_models": sum(len(v) for v in models_by_layer.values()),
        "total_tests": len([k for k in nodes.keys() if k.startswith("test.")]),
        "models_by_layer": models_by_layer,
        "total_dag_edges": len(edges),
        "dag_edges": edges,
        "column_coverage": {
            "total_columns": total_columns,
            "documented_columns": documented_columns,
            "coverage_percentage": round((documented_columns / total_columns * 100), 2) if total_columns > 0 else 0.0
        }
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n==================================================")
    print("dbt LINEAGE & CATALOG EXTRACTION COMPLETE")
    print("==================================================")
    print(f"Total Sources: {summary['total_sources']}")
    print(f"Total Models:  {summary['total_models']} ({summary['models_by_layer']})")
    print(f"Total Tests:   {summary['total_tests']}")
    print(f"Total Edges:   {summary['total_dag_edges']}")
    print(f"Col Coverage:  {summary['column_coverage']['coverage_percentage']}% ({documented_columns}/{total_columns})")
    print(f"Summary JSON:  {OUTPUT_JSON_PATH}")
    print("==================================================")

if __name__ == "__main__":
    extract_lineage()
