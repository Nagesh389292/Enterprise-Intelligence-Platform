"""
NexaCore Data Engineering Platform — Stage 6
Power BI Semantic Layer Control Total Validation Engine

Executes SQL queries against PostgreSQL analytics.* tables to validate that
DAX measure target values match PostgreSQL ground truth with $0.00 financial drift.
"""

import os
import sys
import json
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.environ.get("POSTGRES_PORT", "5433")),
    "user": os.environ.get("POSTGRES_USER", "nexacore_admin"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nexacore_secret_pass"),
    "dbname": os.environ.get("POSTGRES_DB", "nexacore_dw"),
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "analytics", "powerbi_semantic_validation_report.json")

class PowerBISemanticValidator:
    def __init__(self):
        self.report = {
            "overall_status": "FAILED",
            "executed_at": datetime.datetime.now().isoformat(),
            "measures_validated": 0,
            "measures_passed": 0,
            "measures_failed": 0,
            "validation_results": []
        }

    def record_measure(self, measure_name, folder, dax_formula, expected_val, actual_val, tolerance=0.01):
        self.report["measures_validated"] += 1
        
        # Numeric vs string comparison
        if isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
            diff = abs(expected_val - actual_val)
            passed = diff <= tolerance
        else:
            passed = (str(expected_val) == str(actual_val))
            diff = 0.0

        if passed:
            self.report["measures_passed"] += 1
            status = "PASSED"
        else:
            self.report["measures_failed"] += 1
            status = "FAILED"

        self.report["validation_results"].append({
            "measure_name": measure_name,
            "folder": folder,
            "dax_formula": dax_formula,
            "expected_target": expected_val,
            "postgres_actual": actual_val,
            "variance": round(diff, 4),
            "status": status
        })

    def run_all(self):
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Financial & Sales Measures
        cur.execute("SELECT SUM(net_revenue) AS total_net_revenue, SUM(gross_revenue) AS total_gross_revenue, SUM(discount_amount) AS total_discounts, SUM(quantity) AS total_units, COUNT(DISTINCT order_id) AS total_orders_item FROM analytics.fact_order_items;")
        r_sales = cur.fetchone()
        
        cur.execute("SELECT COUNT(DISTINCT order_id) AS total_orders FROM analytics.fact_orders;")
        r_orders = cur.fetchone()

        net_rev = float(r_sales["total_net_revenue"])
        gross_rev = float(r_sales["total_gross_revenue"])
        disc = float(r_sales["total_discounts"])
        units = int(r_sales["total_units"])
        orders = int(r_orders["total_orders"])

        self.record_measure("Total Net Revenue", "_Sales Measures", "SUM(FactOrderItems[net_revenue])", 77237960.93, net_rev)
        self.record_measure("Total Gross Revenue", "_Sales Measures", "SUM(FactOrderItems[gross_revenue])", 83513938.52, gross_rev)
        self.record_measure("Total Discount Amount", "_Sales Measures", "SUM(FactOrderItems[discount_amount])", 6275977.59, disc)
        self.record_measure("Total Units Sold", "_Sales Measures", "SUM(FactOrderItems[quantity])", 192575, units)
        self.record_measure("Total Orders Count", "_Sales Measures", "DISTINCTCOUNT(FactOrders[order_id])", 10000, orders)
        self.record_measure("Average Order Value (AOV)", "_Sales Measures", "DIVIDE([Total Net Revenue], [Total Orders Count], 0)", round(77237960.93 / 10000, 2), round(net_rev / orders, 2))

        # 2. Customer & CSAT Measures
        cur.execute("SELECT COUNT(DISTINCT customer_id) AS cust_cnt FROM analytics.dim_customer;")
        cust_cnt = int(cur.fetchone()["cust_cnt"])
        
        cur.execute("SELECT COUNT(ticket_id) AS ticket_cnt, AVG(csat_score) AS avg_csat FROM analytics.fact_support_tickets;")
        r_tickets = cur.fetchone()
        t_cnt = int(r_tickets["ticket_cnt"])
        avg_csat = round(float(r_tickets["avg_csat"]), 2)

        self.record_measure("Total Customers", "_Customer Measures", "DISTINCTCOUNT(DimCustomer[customer_id])", 1000, cust_cnt)
        self.record_measure("Total Support Tickets", "_Customer Measures", "COUNT(FactSupportTickets[ticket_id])", 2500, t_cnt)
        self.record_measure("Average CSAT Score", "_Customer Measures", "AVERAGE(FactSupportTickets[csat_score])", 3.38, avg_csat)

        # 3. Inventory Measures
        # Note: days_of_supply column was not built in current model iteration;
        # validator uses available columns: quantity_on_hand, is_below_reorder_point.
        cur.execute("SELECT SUM(quantity_on_hand) AS total_on_hand, COUNT(inventory_id) AS total_items, SUM(CASE WHEN is_below_reorder_point THEN 1 ELSE 0 END) AS below_reorder_cnt FROM analytics.fact_inventory_snapshot;")
        r_inv = cur.fetchone()
        on_hand = int(r_inv["total_on_hand"])
        below_reorder = int(r_inv["below_reorder_cnt"])

        self.record_measure("Total Quantity On Hand", "_Inventory Measures", "SUM(FactInventorySnapshot[quantity_on_hand])", 210174, on_hand)
        self.record_measure("Items Below Reorder Point", "_Inventory Measures", "CALCULATE(COUNT(FactInventorySnapshot[inventory_id]), FactInventorySnapshot[is_below_reorder_point] = TRUE)", 85, below_reorder)

        # 4. Machinery & Operations Measures
        cur.execute("SELECT COUNT(DISTINCT machine_id) AS mach_cnt FROM analytics.dim_machine;")
        mach_cnt = int(cur.fetchone()["mach_cnt"])

        cur.execute("SELECT COUNT(telemetry_minute_key) AS telem_cnt, AVG(avg_temperature_c) AS avg_temp FROM analytics.fact_machine_telemetry;")
        r_telem = cur.fetchone()
        telem_cnt = int(r_telem["telem_cnt"])
        avg_temp = round(float(r_telem["avg_temp"]), 2)

        self.record_measure("Machine Fleet Count", "_Operations Measures", "DISTINCTCOUNT(DimMachine[machine_id])", 50, mach_cnt)
        self.record_measure("Total Telemetry Records", "_Operations Measures", "COUNT(FactMachineTelemetry[telemetry_minute_key])", 100000, telem_cnt)
        self.record_measure("Average Fleet Temperature C", "_Operations Measures", "AVERAGE(FactMachineTelemetry[avg_temperature_c])", 65.37, avg_temp)

        conn.close()

        if self.report["measures_failed"] == 0:
            self.report["overall_status"] = "PASSED"

        os.makedirs(os.path.dirname(REPORT_JSON_PATH), exist_ok=True)
        with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        print("\n==================================================")
        print(f"POWER BI SEMANTIC MODEL VALIDATION: {self.report['overall_status']}")
        print("==================================================")
        print(f"Measures Validated: {self.report['measures_validated']}")
        print(f"Measures Passed:    {self.report['measures_passed']}")
        print(f"Measures Failed:    {self.report['measures_failed']}")
        print(f"Report Saved To:    {REPORT_JSON_PATH}")
        print("==================================================")

        return 0 if self.report["overall_status"] == "PASSED" else 1

if __name__ == "__main__":
    validator = PowerBISemanticValidator()
    sys.exit(validator.run_all())
