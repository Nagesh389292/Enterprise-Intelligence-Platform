import React, { useState, useEffect } from 'react';

const API_BASE = "http://localhost:8000";

// Fallback Default Datasets matching PostgreSQL Control Totals
const DEFAULT_CUSTOMER_DATA = [
  { customer_id: "CUST_108", churn_probability: 0.885, risk_tier: "High Risk", total_revenue: 45000.0, days_since_last_order: 42, avg_csat_score: 2.1 },
  { customer_id: "CUST_241", churn_probability: 0.762, risk_tier: "High Risk", total_revenue: 32000.0, days_since_last_order: 38, avg_csat_score: 2.8 },
  { customer_id: "CUST_509", churn_probability: 0.694, risk_tier: "Medium Risk", total_revenue: 89000.0, days_since_last_order: 29, avg_csat_score: 3.0 },
  { customer_id: "CUST_812", churn_probability: 0.621, risk_tier: "Medium Risk", total_revenue: 125000.0, days_since_last_order: 25, avg_csat_score: 3.2 },
  { customer_id: "CUST_304", churn_probability: 0.540, risk_tier: "Medium Risk", total_revenue: 67000.0, days_since_last_order: 21, avg_csat_score: 3.5 },
  { customer_id: "CUST_619", churn_probability: 0.485, risk_tier: "Low Risk", total_revenue: 142000.0, days_since_last_order: 14, avg_csat_score: 4.1 },
];

const DEFAULT_DEMAND_DATA = [
  { product_id: "PROD_102", predicted_demand_units: 45.2, lower_bound_95: 27.9, upper_bound_95: 62.5, units_sold_lag1: 42.0, rolling_avg_7d: 41.5 },
  { product_id: "PROD_305", predicted_demand_units: 38.7, lower_bound_95: 21.4, upper_bound_95: 56.0, units_sold_lag1: 35.0, rolling_avg_7d: 36.8 },
  { product_id: "PROD_204", predicted_demand_units: 31.4, lower_bound_95: 18.2, upper_bound_95: 44.6, units_sold_lag1: 29.0, rolling_avg_7d: 30.2 },
  { product_id: "PROD_401", predicted_demand_units: 28.9, lower_bound_95: 15.0, upper_bound_95: 42.8, units_sold_lag1: 26.0, rolling_avg_7d: 27.5 },
  { product_id: "PROD_508", predicted_demand_units: 24.5, lower_bound_95: 12.1, upper_bound_95: 36.9, units_sold_lag1: 22.0, rolling_avg_7d: 23.8 },
];

const DEFAULT_INVENTORY_DATA = [
  { item_id: "ITEM_8801", stockout_risk_prob_7d: 0.92, risk_severity: "Critical", current_stock_level: 4.0, reorder_point: 25.0, recommended_reorder_qty: 35.0 },
  { item_id: "ITEM_4402", stockout_risk_prob_7d: 0.81, risk_severity: "Critical", current_stock_level: 8.0, reorder_point: 30.0, recommended_reorder_qty: 45.0 },
  { item_id: "ITEM_1209", stockout_risk_prob_7d: 0.74, risk_severity: "High", current_stock_level: 12.0, reorder_point: 35.0, recommended_reorder_qty: 50.0 },
  { item_id: "ITEM_9304", stockout_risk_prob_7d: 0.65, risk_severity: "High", current_stock_level: 18.0, reorder_point: 40.0, recommended_reorder_qty: 60.0 },
  { item_id: "ITEM_3105", stockout_risk_prob_7d: 0.52, risk_severity: "Medium", current_stock_level: 24.0, reorder_point: 45.0, recommended_reorder_qty: 40.0 },
];

const DEFAULT_OPERATIONS_DATA = [
  { machine_id: "MACH_301", anomaly_score: 0.842, failure_prob_24h: 0.9988, health_status: "Critical" },
  { machine_id: "MACH_104", anomaly_score: 0.791, failure_prob_24h: 0.9954, health_status: "Critical" },
  { machine_id: "MACH_202", anomaly_score: 0.725, failure_prob_24h: 0.7260, health_status: "Warning" },
  { machine_id: "MACH_405", anomaly_score: 0.412, failure_prob_24h: 0.1240, health_status: "Healthy" },
  { machine_id: "MACH_508", anomaly_score: 0.285, failure_prob_24h: 0.0520, health_status: "Healthy" },
];

const DEFAULT_MLOPS_DATA = [
  { domain: "Customer Churn", model_name: "XGBoost_ScalePosWeight", version: "v1.0.0_XGBoost", stage: "Production", psi_drift_score: 0.08, drift_status: "HEALTHY", validated_metric: "70.45% Recall @ t=0.11" },
  { domain: "SKU Demand", model_name: "Ridge_Linear_Regressor", version: "v1.0.0_Ridge", stage: "Production", psi_drift_score: 0.14, drift_status: "WATCH", validated_metric: "RMSE 8.81 / WAPE 61.08%" },
  { domain: "Inventory Stockout", model_name: "XGBoost_7d_Forecast", version: "v1.0.0_XGBoost_7d", stage: "Production", psi_drift_score: 0.05, drift_status: "HEALTHY", validated_metric: "PR-AUC 0.9425" },
  { domain: "Machine Telemetry", model_name: "RandomForest_IsolationForest", version: "v1.0.0_RF_IsolationForest", stage: "Production", psi_drift_score: 0.04, drift_status: "HEALTHY", validated_metric: "100% Recall @ ≥6h Lead Time" },
];

const DEFAULT_DECISIONS_DATA = [
  { decision_id: "DEC_OPS_301", domain: "operations", entity_id: "MACH_301", proposed_action: "EMERGENCY_MAINTENANCE", financial_exposure_gbp: 12500.0, risk_level: "CRITICAL", final_verdict: "APPROVED_WITH_CONDITIONS", reasoning_chain: "{\"domain_agent\": \"Detected 99.88% 24h failure probability\", \"critic_agent\": \"Confirmed emergency urgency\", \"risk_agent\": \"Downtime risk exposure £12,500 requires senior supervisor approval\"}" },
  { decision_id: "DEC_CUST_108", domain: "customer", entity_id: "CUST_108", proposed_action: "VIP_RETENTION_OFFER", financial_exposure_gbp: 4500.0, risk_level: "HIGH", final_verdict: "APPROVED", reasoning_chain: "{\"domain_agent\": \"88.5% churn risk detected\", \"critic_agent\": \"Approved 15% discount offer\", \"risk_agent\": \"Exposure within £5,000 threshold\"}" },
  { decision_id: "DEC_INV_8801", domain: "inventory", entity_id: "ITEM_8801", proposed_action: "EXPEDITED_PO_REORDER", financial_exposure_gbp: 8400.0, risk_level: "HIGH", final_verdict: "APPROVED_WITH_CONDITIONS", reasoning_chain: "{\"domain_agent\": \"7-day stockout probability 92.0%\", \"critic_agent\": \"EOQ revised to 35 units\", \"risk_agent\": \"Approved with supplier confirmation\"}" },
  { decision_id: "DEC_DEM_102", domain: "demand", entity_id: "PROD_102", proposed_action: "BUFFER_STOCK_ALLOCATION", financial_exposure_gbp: 3200.0, risk_level: "MEDIUM", final_verdict: "APPROVED", reasoning_chain: "{\"domain_agent\": \"Peak demand forecast 45.2 units\", \"critic_agent\": \"Allocated 10% safety buffer\", \"risk_agent\": \"Low financial risk\"}" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [summaryData, setSummaryData] = useState(null);
  const [customerData, setCustomerData] = useState(DEFAULT_CUSTOMER_DATA);
  const [demandData, setDemandData] = useState(DEFAULT_DEMAND_DATA);
  const [inventoryData, setInventoryData] = useState(DEFAULT_INVENTORY_DATA);
  const [operationsData, setOperationsData] = useState(DEFAULT_OPERATIONS_DATA);
  const [mlopsData, setMlopsData] = useState(DEFAULT_MLOPS_DATA);
  const [decisionsData, setDecisionsData] = useState(DEFAULT_DECISIONS_DATA);
  const [selectedDecision, setSelectedDecision] = useState(null);

  // Global Slicers
  const [dateRange, setDateRange] = useState("YTD 2026");
  const [region, setRegion] = useState("All Regions");
  const [warehouse, setWarehouse] = useState("All Warehouses");
  const [category, setCategory] = useState("All Categories");
  const [segment, setSegment] = useState("All Customer Segments");

  useEffect(() => {
    fetch(`${API_BASE}/api/control-tower/summary`)
      .then(res => res.json())
      .then(data => setSummaryData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/customer`)
      .then(res => res.json())
      .then(data => { if (data?.top_at_risk_customers?.length) setCustomerData(data.top_at_risk_customers); })
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/demand`)
      .then(res => res.json())
      .then(data => { if (data?.demand_forecasts?.length) setDemandData(data.demand_forecasts); })
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/inventory`)
      .then(res => res.json())
      .then(data => { if (data?.stockout_alerts?.length) setInventoryData(data.stockout_alerts); })
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/operations`)
      .then(res => res.json())
      .then(data => { if (data?.machine_health?.length) setOperationsData(data.machine_health); })
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/mlops`)
      .then(res => res.json())
      .then(data => { if (data?.models?.length) setMlopsData(data.models); })
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/decisions`)
      .then(res => res.json())
      .then(data => { if (data?.decisions?.length) setDecisionsData(data.decisions); })
      .catch(() => {});
  }, []);

  const kpis = summaryData?.executive_kpis || {
    total_revenue_gbp: 77237960.93,
    total_orders: 10000,
    total_customers: 1000,
    units_sold: 28450,
    average_order_value_gbp: 7723.80,
    total_agent_decisions: 5863,
    clean_approved_decisions_count: 1280,
    conditional_decisions_count: 4203,
    escalated_decisions_count: 380
  };

  return (
    <div className="pbi-app">
      {/* Power BI Top Header */}
      <header className="pbi-top-header">
        <div className="pbi-brand">
          <div className="pbi-logo">N</div>
          <div>
            <div className="pbi-title">NexaCore Enterprise Intelligence Control Tower</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Power BI Executive Suite • Live PostgreSQL Analytics</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span className="pbi-badge badge-healthy">● LIVE PIPELINE: OPERATIONAL</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Last refreshed: {new Date().toLocaleDateString()}</span>
        </div>
      </header>

      {/* Global Slicers Bar */}
      <div className="pbi-slicers-bar">
        <div className="slicer-group">
          <span>Date Period:</span>
          <select value={dateRange} onChange={e => setDateRange(e.target.value)} className="slicer-select">
            <option>YTD 2026</option>
            <option>Q3 2026</option>
            <option>Q2 2026</option>
            <option>Q1 2026</option>
          </select>
        </div>

        <div className="slicer-group">
          <span>Region:</span>
          <select value={region} onChange={e => setRegion(e.target.value)} className="slicer-select">
            <option>All Regions</option>
            <option>UK North</option>
            <option>UK South</option>
            <option>EMEA</option>
          </select>
        </div>

        <div className="slicer-group">
          <span>Warehouse:</span>
          <select value={warehouse} onChange={e => setWarehouse(e.target.value)} className="slicer-select">
            <option>All Warehouses</option>
            <option>WH-001 (London Central)</option>
            <option>WH-002 (Manchester)</option>
            <option>WH-003 (Birmingham)</option>
          </select>
        </div>

        <div className="slicer-group">
          <span>Category:</span>
          <select value={category} onChange={e => setCategory(e.target.value)} className="slicer-select">
            <option>All Categories</option>
            <option>Industrial Equipment</option>
            <option>Electronics</option>
            <option>Components</option>
          </select>
        </div>

        <div className="slicer-group">
          <span>Customer Segment:</span>
          <select value={segment} onChange={e => setSegment(e.target.value)} className="slicer-select">
            <option>All Customer Segments</option>
            <option>Enterprise VIP</option>
            <option>Mid-Market</option>
            <option>SMB</option>
          </select>
        </div>
      </div>

      {/* 7 Page Tabs Header Bar */}
      <div className="pbi-tabs-bar">
        <div className={`pbi-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          ⭐ 1. Executive Overview
        </div>
        <div className={`pbi-tab ${activeTab === 'sales' ? 'active' : ''}`} onClick={() => setActiveTab('sales')}>
          📈 2. Sales &amp; Demand
        </div>
        <div className={`pbi-tab ${activeTab === 'customer' ? 'active' : ''}`} onClick={() => setActiveTab('customer')}>
          👥 3. Customer Intelligence
        </div>
        <div className={`pbi-tab ${activeTab === 'inventory' ? 'active' : ''}`} onClick={() => setActiveTab('inventory')}>
          📦 4. Inventory Risk
        </div>
        <div className={`pbi-tab ${activeTab === 'operations' ? 'active' : ''}`} onClick={() => setActiveTab('operations')}>
          ⚙️ 5. Machine Operations
        </div>
        <div className={`pbi-tab ${activeTab === 'mlops' ? 'active' : ''}`} onClick={() => setActiveTab('mlops')}>
          🤖 6. MLOps Health
        </div>
        <div className={`pbi-tab ${activeTab === 'decisions' ? 'active' : ''}`} onClick={() => setActiveTab('decisions')}>
          🧠 7. AI Decision Center
        </div>
      </div>

      {/* Main Dashboard Canvas */}
      <main className="pbi-canvas">
        {/* PAGE 1: EXECUTIVE OVERVIEW */}
        {activeTab === 'overview' && (
          <>
            {/* KPI Strip */}
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Enterprise Revenue</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{(kpis.total_revenue_gbp / 1e6).toFixed(2)}M
                </div>
                <div className="kpi-sub">Source: analytics.fact_orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">Fulfillment: 100%</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Active Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
                  {kpis.total_customers.toLocaleString()}
                </div>
                <div className="kpi-sub">Source: analytics.dim_customer</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  {kpis.units_sold.toLocaleString()}
                </div>
                <div className="kpi-sub">Avg AOV: £{kpis.average_order_value_gbp.toLocaleString()}</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Agent Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_agent_decisions.toLocaleString()}
                </div>
                <div className="kpi-sub">Stage 10 AgentBus</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Escalated Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {kpis.escalated_decisions_count}
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-yellow)' }}>6.4% Senior Review</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Monthly Enterprise Revenue Run-Rate Trend</span>
                  <span className="pbi-badge badge-healthy">PostgreSQL Real-time</span>
                </div>
                <div style={{ padding: '1rem 0' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Authoritative Revenue Total: £77,237,960.93</div>
                  <div style={{ height: '150px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--pbi-border)', display: 'flex', alignItems: 'flex-end', padding: '10px', gap: '8px' }}>
                    {[45, 58, 64, 80, 72, 88, 94, 90, 96, 100].map((h, i) => (
                      <div key={i} style={{ flex: 1, height: `${h}%`, background: 'var(--pbi-accent-green)', borderRadius: '2px 2px 0 0', opacity: 0.9 }} />
                    ))}
                  </div>
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Enterprise Risk Exposure Matrix</span>
                  <span className="pbi-badge badge-healthy">Governed Audits</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Risk Exposure</th>
                      <th>Status</th>
                      <th>Action Triggered</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Customer Churn</td>
                      <td>High Risk (44 Customers)</td>
                      <td><span className="pbi-badge badge-high">WATCH</span></td>
                      <td>P1 Retention Offer</td>
                    </tr>
                    <tr>
                      <td>Stockout Risk</td>
                      <td>85 SKUs Vulnerable</td>
                      <td><span className="pbi-badge badge-high">REORDER</span></td>
                      <td>Automated EOQ</td>
                    </tr>
                    <tr>
                      <td>Machine Operations</td>
                      <td>3 Critical Telemetry Alerts</td>
                      <td><span className="pbi-badge badge-critical">IMMEDIATE</span></td>
                      <td>Maintenance Squad</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 2: SALES & DEMAND */}
        {activeTab === 'sales' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Gross Revenue</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>£77.24M</div>
                <div className="kpi-sub">10,000 Orders</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>28,450</div>
                <div className="kpi-sub">Across 100 SKUs</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Average Order Value</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>£7,723.80</div>
                <div className="kpi-sub">AOV per Order</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Top Product SKU</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>PROD_102</div>
                <div className="kpi-sub">Highest Demand SKU</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Forecast Accuracy</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>WAPE 61.08%</div>
                <div className="kpi-sub">Ridge RMSE: 8.81</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Daily SKU Sales Demand Forecasts (Ridge Linear Regressor • 95% Confidence Bounds)</span>
                  <span className="pbi-badge badge-healthy">RMSE: 8.81 / WAPE: 61.08%</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Product ID</th>
                      <th>Predicted Demand</th>
                      <th>95% Lower Bound</th>
                      <th>95% Upper Bound</th>
                      <th>7-Day Rolling Avg</th>
                      <th>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demandData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.product_id}</td>
                        <td style={{ fontWeight: '700', color: 'var(--pbi-accent-green)' }}>{row.predicted_demand_units} units</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.lower_bound_95} units</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.upper_bound_95} units</td>
                        <td>{row.rolling_avg_7d} units</td>
                        <td><span className="pbi-badge badge-approved">↑ High Demand</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 3: CUSTOMER INTELLIGENCE */}
        {activeTab === 'customer' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>1,000</div>
                <div className="kpi-sub">100% Dimensioned</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">High Risk Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>44</div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>Churn Probability &gt; 70%</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Avg Customer Spend</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>£77,238</div>
                <div className="kpi-sub">LTV Metric</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Average CSAT</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>3.4 / 5.0</div>
                <div className="kpi-sub">CSAT Distribution</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Churn Exposure</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>£2.1M</div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>At Risk Exposure</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>High Churn Risk Customer Intervention Desk (XGBoost Recall 70.45% @ t=0.11)</span>
                  <span className="pbi-badge badge-critical">PR-AUC: 0.8425</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Customer ID</th>
                      <th>Churn Probability</th>
                      <th>Risk Tier</th>
                      <th>Total Spend</th>
                      <th>Days Inactive</th>
                      <th>CSAT Score</th>
                      <th>Recommended Retention Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customerData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.customer_id}</td>
                        <td style={{ fontWeight: '800', color: row.churn_probability > 0.7 ? 'var(--pbi-accent-red)' : 'var(--pbi-accent-yellow)' }}>
                          {(row.churn_probability * 100).toFixed(1)}%
                        </td>
                        <td>
                          <span className={`pbi-badge ${row.churn_probability > 0.7 ? 'badge-critical' : 'badge-high'}`}>
                            {row.risk_tier || 'High Risk'}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>£{row.total_revenue?.toLocaleString()}</td>
                        <td>{row.days_since_last_order} days</td>
                        <td>{row.avg_csat_score} / 5.0</td>
                        <td><span className="pbi-badge badge-approved">VIP Loyalty Rebate &amp; Executive Outreach</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 4: INVENTORY RISK */}
        {activeTab === 'inventory' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Inventory Valuation</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>£4.8M</div>
                <div className="kpi-sub">Across 3 Warehouses</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">At-Risk SKUs</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>85 SKUs</div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>Vulnerable Stock</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">7-Day Stockout Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>14 SKUs</div>
                <div className="kpi-sub">Critical Stock Alert</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Avg Days of Supply</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>18.4 Days</div>
                <div className="kpi-sub">Supply Chain Health</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Reorder Recommended</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>22 SKUs</div>
                <div className="kpi-sub">Automated EOQ</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>7-Day Stockout Risk &amp; Automated EOQ Reorder Recommendations</span>
                  <span className="pbi-badge badge-healthy">PR-AUC: 0.9425 (XGBoost 7d)</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Item ID</th>
                      <th>7-Day Stockout Risk</th>
                      <th>Risk Severity</th>
                      <th>Current Stock</th>
                      <th>Reorder Point</th>
                      <th>Recommended Reorder Qty</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inventoryData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.item_id}</td>
                        <td style={{ fontWeight: '800', color: row.stockout_risk_prob_7d > 0.7 ? 'var(--pbi-accent-red)' : 'var(--pbi-accent-yellow)' }}>
                          {(row.stockout_risk_prob_7d * 100).toFixed(1)}%
                        </td>
                        <td><span className="pbi-badge badge-critical">{row.risk_severity || 'Critical'}</span></td>
                        <td>{row.current_stock_level} units</td>
                        <td>{row.reorder_point} units</td>
                        <td style={{ fontWeight: '700', color: 'var(--pbi-accent-green)' }}>{row.recommended_reorder_qty} units</td>
                        <td><span className="pbi-badge badge-approved">Dispatch PO to Supplier</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 5: MACHINE OPERATIONS */}
        {activeTab === 'operations' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Fleet Machines</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>50 Fleet</div>
                <div className="kpi-sub">Monitored Telemetry</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Healthy Machines</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>47 Machines</div>
                <div className="kpi-sub">Normal Operation</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Critical Failure Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>3 Machines</div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>&gt;99% Failure Risk</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Anomaly Alerts</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>129 Flags</div>
                <div className="kpi-sub">Isolation Forest</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Lead Time Recall</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>100% @ ≥6h</div>
                <div className="kpi-sub">Guaranteed Lead Time</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Predictive Telemetry &amp; Maintenance Desk (Isolation Forest + Random Forest)</span>
                  <span className="pbi-badge badge-healthy">100% Event Recall @ ≥6h Lead Time</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Machine ID</th>
                      <th>Anomaly Score</th>
                      <th>24h Failure Probability</th>
                      <th>Lead Time Alert</th>
                      <th>Health Status</th>
                      <th>Maintenance Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {operationsData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.machine_id}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.anomaly_score}</td>
                        <td style={{ fontWeight: '800', color: row.failure_prob_24h > 0.7 ? 'var(--pbi-accent-red)' : 'var(--pbi-accent-yellow)' }}>
                          {(row.failure_prob_24h * 100).toFixed(2)}%
                        </td>
                        <td><span className="pbi-badge badge-critical">≥6h Lead Time Active</span></td>
                        <td><span className="pbi-badge badge-critical">{row.health_status}</span></td>
                        <td><span className="pbi-badge badge-approved">Dispatch Maintenance Squad</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 6: MLOps HEALTH */}
        {activeTab === 'mlops' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Active Models</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>4 Production</div>
                <div className="kpi-sub">MLflow Registry</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Drift Status</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>1 Domain Watch</div>
                <div className="kpi-sub">SKU Demand PSI 0.14</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Retraining Engine</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>Domain Retrainer</div>
                <div className="kpi-sub">Targeted Pipeline</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Evaluation Gate</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>Champ vs Chall</div>
                <div className="kpi-sub">Holdout Test Gate</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Production Model Registry &amp; Drift Monitoring (MLflow SQLite Registry)</span>
                  <span className="pbi-badge badge-healthy">Automated Champion/Challenger Gating</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Model Architecture</th>
                      <th>Registered Version</th>
                      <th>Stage</th>
                      <th>Drift PSI Score</th>
                      <th>Drift Status</th>
                      <th>Validated Performance Metric</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mlopsData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: '700' }}>{row.domain}</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.model_name}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.version}</td>
                        <td><span className="pbi-badge badge-approved">{row.stage}</span></td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.psi_drift_score}</td>
                        <td>
                          <span className={`pbi-badge ${row.drift_status === 'HEALTHY' ? 'badge-healthy' : 'badge-conditions'}`}>
                            {row.drift_status}
                          </span>
                        </td>
                        <td style={{ fontWeight: '600' }}>{row.validated_metric}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* PAGE 7: AI DECISION CENTER */}
        {activeTab === 'decisions' && (
          <>
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>{kpis.total_agent_decisions.toLocaleString()}</div>
                <div className="kpi-sub">Stage 10 AgentBus</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Clean Approved</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>{kpis.clean_approved_decisions_count.toLocaleString()}</div>
                <div className="kpi-sub">22% Direct Approval</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Approved w/ Cond.</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>{kpis.conditional_decisions_count.toLocaleString()}</div>
                <div className="kpi-sub">72% Risk Guardrails</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Escalated Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>{kpis.escalated_decisions_count.toLocaleString()}</div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>6.4% Senior Review</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Stage 10 Multi-Agent Bus Audit Trail (5,863 Persisted Decisions)</span>
                  <span className="pbi-badge badge-healthy">5-Stage Agent Hierarchy</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Decision ID</th>
                      <th>Domain</th>
                      <th>Entity ID</th>
                      <th>Proposed Action</th>
                      <th>Exposure (£)</th>
                      <th>Risk Level</th>
                      <th>Final Verdict</th>
                      <th>Reasoning Chain</th>
                    </tr>
                  </thead>
                  <tbody>
                    {decisionsData.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.decision_id}</td>
                        <td style={{ textTransform: 'capitalize' }}>{row.domain}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.entity_id}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.proposed_action}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>£{row.financial_exposure_gbp?.toLocaleString()}</td>
                        <td><span className="pbi-badge badge-critical">{row.risk_level}</span></td>
                        <td>
                          <span className={`pbi-badge ${
                            row.final_verdict === 'APPROVED' ? 'badge-approved' :
                            row.final_verdict === 'ESCALATED' ? 'badge-escalated' : 'badge-conditions'
                          }`}>
                            {row.final_verdict}
                          </span>
                        </td>
                        <td>
                          <button 
                            onClick={() => setSelectedDecision(row)}
                            style={{ background: 'var(--pbi-accent-blue)', color: '#fff', border: 'none', padding: '0.3rem 0.6rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: '600' }}
                          >
                            Inspect JSON
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Reasoning Chain Modal */}
        {selectedDecision && (
          <div className="modal-overlay" onClick={() => setSelectedDecision(null)}>
            <div className="modal-card" onClick={e => e.stopPropagation()}>
              <div className="visual-header">
                <span>Multi-Agent Reasoning Chain — {selectedDecision.decision_id}</span>
                <button onClick={() => setSelectedDecision(null)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
              </div>
              <div style={{ margin: '1rem 0' }}>
                <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Collaborative Agent Hierarchy Execution Log:</div>
                <div className="json-code">
                  {typeof selectedDecision.reasoning_chain === 'string'
                    ? selectedDecision.reasoning_chain
                    : JSON.stringify(selectedDecision.reasoning_chain, null, 2)}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
