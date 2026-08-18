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
    
    # 1. Fact Row Counts & Variances
    fact_counts = {}
    
    # Orders
    cur.execute("SELECT COUNT(*) FROM source.orders;")
    src_orders = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_orders;")
    gold_orders = cur.fetchone()["count"]
    fact_counts["fact_orders"] = {"silver": src_orders, "gold": gold_orders, "variance": gold_orders - src_orders}

    # Order Items
    cur.execute("SELECT COUNT(*) FROM source.order_items;")
    src_items = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_order_items;")
    gold_items = cur.fetchone()["count"]
    fact_counts["fact_order_items"] = {"silver": src_items, "gold": gold_items, "variance": gold_items - src_items}

    # Inventory Snapshot
    cur.execute("SELECT COUNT(*) FROM source.inventory;")
    src_inv = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_inventory_snapshot;")
    gold_inv = cur.fetchone()["count"]
    fact_counts["fact_inventory_snapshot"] = {"silver": src_inv, "gold": gold_inv, "variance": gold_inv - src_inv}

    # Maintenance Events
    cur.execute("SELECT COUNT(*) FROM source.maintenance_events;")
    src_maint = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_maintenance_events;")
    gold_maint = cur.fetchone()["count"]
    fact_counts["fact_maintenance_events"] = {"silver": src_maint, "gold": gold_maint, "variance": gold_maint - src_maint}

    # Support Tickets
    cur.execute("SELECT COUNT(*) FROM source.support_tickets;")
    src_tickets = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_support_tickets;")
    gold_tickets = cur.fetchone()["count"]
    fact_counts["fact_support_tickets"] = {"silver": src_tickets, "gold": gold_tickets, "variance": gold_tickets - src_tickets}

    # Telemetry Aggregation Specs
    cur.execute("SELECT COUNT(*) FROM source.machine_telemetry;")
    raw_telemetry_count = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM analytics.fact_machine_telemetry;")
    gold_telemetry_count = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(DISTINCT machine_id) FROM analytics.fact_machine_telemetry;")
    telemetry_machines = cur.fetchone()["count"]
    cur.execute("SELECT MIN(minute_timestamp), MAX(minute_timestamp) FROM analytics.fact_machine_telemetry;")
    telemetry_dates = cur.fetchone()
    
    telemetry_specs = {
        "raw_telemetry_count": raw_telemetry_count,
        "gold_telemetry_1min_count": gold_telemetry_count,
        "machines_represented": telemetry_machines,
        "min_timestamp": str(telemetry_dates["min"]),
        "max_timestamp": str(telemetry_dates["max"]),
        "aggregation_ratio": round(raw_telemetry_count / gold_telemetry_count, 2) if gold_telemetry_count > 0 else 0
    }

    # 2. Control Totals Comparison
    # Orders Revenue
    cur.execute("SELECT SUM(total_amount)::numeric(12,2) FROM source.orders;")
    src_rev_val = cur.fetchone()["sum"]
    src_order_rev = float(src_rev_val) if src_rev_val is not None else 0.0
    cur.execute("SELECT SUM(total_amount)::numeric(12,2) FROM analytics.fact_orders;")
    gold_rev_val = cur.fetchone()["sum"]
    gold_order_rev = float(gold_rev_val) if gold_rev_val is not None else 0.0

    # Order Items Revenue & Quantity
    cur.execute("SELECT SUM(total_price)::numeric(12,2) AS net_rev, SUM(quantity) AS qty, SUM(discount_amount)::numeric(12,2) AS discount FROM source.order_items;")
    src_item_metrics = cur.fetchone()
    cur.execute("SELECT SUM(net_revenue)::numeric(12,2) AS net_rev, SUM(quantity) AS qty, SUM(discount_amount)::numeric(12,2) AS discount FROM analytics.fact_order_items;")
    gold_item_metrics = cur.fetchone()

    src_item_net = float(src_item_metrics["net_rev"]) if src_item_metrics["net_rev"] is not None else 0.0
    gold_item_net = float(gold_item_metrics["net_rev"]) if gold_item_metrics["net_rev"] is not None else 0.0
    src_item_qty = int(src_item_metrics["qty"]) if src_item_metrics["qty"] is not None else 0
    gold_item_qty = int(gold_item_metrics["qty"]) if gold_item_metrics["qty"] is not None else 0
    src_item_disc = float(src_item_metrics["discount"]) if src_item_metrics["discount"] is not None else 0.0
    gold_item_disc = float(gold_item_metrics["discount"]) if gold_item_metrics["discount"] is not None else 0.0

    # Inventory Quantities
    cur.execute("SELECT SUM(quantity_on_hand) AS on_hand, SUM(quantity_allocated) AS allocated FROM source.inventory;")
    src_inv_metrics = cur.fetchone()
    cur.execute("SELECT SUM(quantity_on_hand) AS on_hand, SUM(quantity_allocated) AS allocated FROM analytics.fact_inventory_snapshot;")
    gold_inv_metrics = cur.fetchone()

    src_on_hand = int(src_inv_metrics["on_hand"]) if src_inv_metrics["on_hand"] is not None else 0
    gold_on_hand = int(gold_inv_metrics["on_hand"]) if gold_inv_metrics["on_hand"] is not None else 0
    src_alloc = int(src_inv_metrics["allocated"]) if src_inv_metrics["allocated"] is not None else 0
    gold_alloc = int(gold_inv_metrics["allocated"]) if gold_inv_metrics["allocated"] is not None else 0

    # CSAT Score & Surveys
    cur.execute("SELECT COUNT(*) AS total_surveys, AVG(score)::numeric(5,2) AS avg_csat FROM source.customer_satisfaction;")
    src_csat = cur.fetchone()
    cur.execute("SELECT COUNT(csat_survey_id) AS total_surveys, AVG(csat_score)::numeric(5,2) AS avg_csat FROM analytics.fact_support_tickets WHERE csat_survey_id IS NOT NULL;")
    gold_csat = cur.fetchone()

    src_csat_surveys = int(src_csat["total_surveys"]) if src_csat["total_surveys"] is not None else 0
    gold_csat_surveys = int(gold_csat["total_surveys"]) if gold_csat["total_surveys"] is not None else 0
    src_csat_avg = float(src_csat["avg_csat"]) if src_csat["avg_csat"] is not None else 0.0
    gold_csat_avg = float(gold_csat["avg_csat"]) if gold_csat["avg_csat"] is not None else 0.0

    control_totals = {
        "orders_total_revenue": {"silver": src_order_rev, "gold": gold_order_rev, "variance": round(gold_order_rev - src_order_rev, 2)},
        "items_total_quantity": {"silver": src_item_qty, "gold": gold_item_qty, "variance": gold_item_qty - src_item_qty},
        "items_net_revenue": {"silver": src_item_net, "gold": gold_item_net, "variance": round(gold_item_net - src_item_net, 2)},
        "items_total_discount": {"silver": src_item_disc, "gold": gold_item_disc, "variance": round(gold_item_disc - src_item_disc, 2)},
        "inventory_on_hand": {"silver": src_on_hand, "gold": gold_on_hand, "variance": gold_on_hand - src_on_hand},
        "inventory_allocated": {"silver": src_alloc, "gold": gold_alloc, "variance": gold_alloc - src_alloc},
        "csat_total_surveys": {"silver": src_csat_surveys, "gold": gold_csat_surveys, "variance": gold_csat_surveys - src_csat_surveys},
        "csat_avg_score": {"silver": src_csat_avg, "gold": gold_csat_avg, "variance": round(gold_csat_avg - src_csat_avg, 2)}
    }

    # 3. Orphan Checks across Fact Tables
    cur.execute("SELECT COUNT(*) FROM analytics.fact_orders f LEFT JOIN analytics.dim_customer d ON f.customer_id = d.customer_id WHERE d.customer_id IS NULL;")
    orphan_orders_customer = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.fact_order_items f LEFT JOIN analytics.dim_product d ON f.product_id = d.product_id WHERE d.product_id IS NULL;")
    orphan_items_product = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.fact_inventory_snapshot f LEFT JOIN analytics.dim_warehouse d ON f.warehouse_id = d.warehouse_id WHERE d.warehouse_id IS NULL;")
    orphan_inv_warehouse = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.fact_machine_telemetry f LEFT JOIN analytics.dim_machine d ON f.machine_id = d.machine_id WHERE d.machine_id IS NULL;")
    orphan_telemetry_machine = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.fact_maintenance_events f LEFT JOIN analytics.dim_machine d ON f.machine_id = d.machine_id WHERE d.machine_id IS NULL;")
    orphan_maint_machine = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM analytics.fact_support_tickets f LEFT JOIN analytics.dim_customer d ON f.customer_id = d.customer_id WHERE d.customer_id IS NULL;")
    orphan_tickets_customer = cur.fetchone()["count"]

    orphan_summary = {
        "orphan_orders_customer": orphan_orders_customer,
        "orphan_items_product": orphan_items_product,
        "orphan_inv_warehouse": orphan_inv_warehouse,
        "orphan_telemetry_machine": orphan_telemetry_machine,
        "orphan_maint_machine": orphan_maint_machine,
        "orphan_tickets_customer": orphan_tickets_customer,
        "has_orphans": any([
            orphan_orders_customer > 0, orphan_items_product > 0, orphan_inv_warehouse > 0,
            orphan_telemetry_machine > 0, orphan_maint_machine > 0, orphan_tickets_customer > 0
        ])
    }

    results = {
        "fact_counts": fact_counts,
        "telemetry_specs": telemetry_specs,
        "control_totals": control_totals,
        "orphan_summary": orphan_summary
    }

    print(json.dumps(results, indent=2))
    conn.close()

if __name__ == "__main__":
    main()
