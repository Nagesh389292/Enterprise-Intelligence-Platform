import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "user": "nexacore_admin",
    "password": "nexacore_secret_pass",
    "dbname": "nexacore_dw",
}

def inspect():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics' ORDER BY table_name;")
    tables = [r["table_name"] for r in cur.fetchall()]
    print("Tables in analytics schema:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM analytics.{t};")
        cnt = cur.fetchone()["count"]
        print(f"  {t:<35}: {cnt:,} rows")

    print("\n--------------------------------------------------")
    print("ML Feature Mart Detailed Inspection:")
    print("--------------------------------------------------")
    
    # 1. Churn
    cur.execute("SELECT COUNT(*), SUM(is_churned_target) AS churned, AVG(account_tenure_days)::numeric(10,2) AS avg_tenure FROM analytics.ml_customer_churn_features;")
    churn = cur.fetchone()
    print("1. ml_customer_churn_features:")
    print(f"   Total Customers: {churn['count']} | Churned Target (60d post-cutoff): {churn['churned']} ({churn['churned']/churn['count']*100:.1f}%) | Avg Tenure: {churn['avg_tenure']} days")

    # 2. Demand Forecasting
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT product_id) AS products, COUNT(DISTINCT date_key) AS dates, SUM(units_sold_target) AS total_units FROM analytics.ml_demand_forecasting_daily;")
    demand = cur.fetchone()
    print("2. ml_demand_forecasting_daily:")
    print(f"   Total Rows: {demand['count']:,} | Products: {demand['products']} | Dates: {demand['dates']} | Total Units Target: {demand['total_units']:,}")

    # 3. Stockout Risk
    cur.execute("SELECT COUNT(*), SUM(stockout_risk_flag_target) AS stockouts, AVG(days_of_supply)::numeric(10,2) AS avg_dos FROM analytics.ml_inventory_stockout_risk;")
    stockout = cur.fetchone()
    print("3. ml_inventory_stockout_risk:")
    print(f"   Total Snapshots: {stockout['count']} | High Stockout Risk Items (< Reorder Point): {stockout['stockouts']} ({stockout['stockouts']/stockout['count']*100:.1f}%) | Avg Days of Supply: {stockout['avg_dos']}")

    # 4. Telemetry Features
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT machine_id) AS machines, AVG(avg_temperature_c)::numeric(10,2) AS avg_temp, AVG(rolling_10min_avg_temp)::numeric(10,2) AS roll_temp FROM analytics.ml_machine_telemetry_features;")
    tel = cur.fetchone()
    print("4. ml_machine_telemetry_features:")
    print(f"   Total 1-Min Intervals: {tel['count']:,} | Machines: {tel['machines']} | Avg Temp: {tel['avg_temp']} C | 10-Min Rolling Temp: {tel['roll_temp']} C")

    conn.close()

if __name__ == "__main__":
    inspect()
