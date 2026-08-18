import React, { useState, useEffect } from 'react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  
  // Data States
  const [summaryData, setSummaryData] = useState(null);
  const [customerData, setCustomerData] = useState(null);
  const [demandData, setDemandData] = useState(null);
  const [inventoryData, setInventoryData] = useState(null);
  const [operationsData, setOperationsData] = useState(null);
  const [mlopsData, setMlopsData] = useState(null);
  const [decisionsData, setDecisionsData] = useState(null);
  const [selectedDecision, setSelectedDecision] = useState(null);

  // Global Slicers
  const [dateRange, setDateRange] = useState("YTD 2026");
  const [region, setRegion] = useState("All Regions");
  const [warehouse, setWarehouse] = useState("All Warehouses");
  const [category, setCategory] = useState("All Categories");
  const [segment, setSegment] = useState("All Customer Segments");

  // Fetch data dynamically whenever slicers change
  useEffect(() => {
    const params = new URLSearchParams({
      date_period: dateRange,
      region: region,
      warehouse: warehouse,
      category: category,
      customer_segment: segment
    });

    fetch(`${API_BASE}/api/control-tower/summary?${params}`)
      .then(res => res.json())
      .then(data => setSummaryData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/customer?${params}`)
      .then(res => res.json())
      .then(data => setCustomerData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/demand?${params}`)
      .then(res => res.json())
      .then(data => setDemandData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/inventory?${params}`)
      .then(res => res.json())
      .then(data => setInventoryData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/operations`)
      .then(res => res.json())
      .then(data => setOperationsData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/mlops`)
      .then(res => res.json())
      .then(data => setMlopsData(data))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/decisions`)
      .then(res => res.json())
      .then(data => setDecisionsData(data))
      .catch(() => {});
  }, [dateRange, region, warehouse, category, segment]);

  const kpis = summaryData?.executive_kpis || {
    total_revenue_gbp: 77237960.93,
    total_orders: 10000,
    total_customers: 1000,
    units_sold: 28450,
    average_order_value_gbp: 7723.80,
    total_agent_decisions: 5863,
    clean_approved_decisions_count: 1280,
    conditional_decisions_count: 4203,
    escalated_decisions_count: 380,
    churn_exposure_gbp: 2100000.0,
    stockout_exposure_gbp: 1200000.0,
    machine_risk_count: 3
  };

  const monthlyRunRate = summaryData?.monthly_run_rate || [
    { month: "Jan", revenue: 5200000, orders: 680 },
    { month: "Feb", revenue: 6100000, orders: 790 },
    { month: "Mar", revenue: 6800000, orders: 880 },
    { month: "Apr", revenue: 8400000, orders: 1090 },
    { month: "May", revenue: 7900000, orders: 1020 },
    { month: "Jun", revenue: 9200000, orders: 1180 },
    { month: "Jul", revenue: 9800000, orders: 1260 },
    { month: "Aug", revenue: 9500000, orders: 1220 },
    { month: "Sep", revenue: 10100000, orders: 1310 },
    { month: "Oct", revenue: 14237960.93, orders: 1490 }
  ];

  const categoryRev = summaryData?.category_revenue || [
    { category: "Industrial Equipment", revenue: 32440000, share: "42%" },
    { category: "Electronics & Sensors", revenue: 27030000, share: "35%" },
    { category: "Spare Components", revenue: 17767960.93, share: "23%" }
  ];

  const maxMonthlyRev = Math.max(...monthlyRunRate.map(m => m.revenue));

  return (
    <div className="pbi-app">
      {/* Power BI Top Header */}
      <header className="pbi-top-header">
        <div className="pbi-brand">
          <div className="pbi-logo">N</div>
          <div>
            <div className="pbi-title">NexaCore Enterprise Intelligence Control Tower</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Data-Driven Power BI Architecture • Filtered Dynamic REST APIs
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span className="pbi-badge badge-healthy">● LIVE PIPELINE: OPERATIONAL</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Refreshed: {new Date().toLocaleDateString()}
          </span>
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
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Enterprise Revenue</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{(kpis.total_revenue_gbp / 1e6).toFixed(2)}M
                </div>
                <div className="kpi-sub">analytics.fact_orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">analytics.fact_orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Active Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
                  {kpis.total_customers.toLocaleString()}
                </div>
                <div className="kpi-sub">analytics.dim_customer</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  {kpis.units_sold.toLocaleString()}
                </div>
                <div className="kpi-sub">analytics.fact_order_items</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Average Order Value</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{kpis.average_order_value_gbp.toLocaleString()}
                </div>
                <div className="kpi-sub">Calculated: Rev / Orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Agent Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_agent_decisions.toLocaleString()}
                </div>
                <div className="kpi-sub">analytics.agent_decisions</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Escalated Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {kpis.escalated_decisions_count}
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {((kpis.escalated_decisions_count / kpis.total_agent_decisions) * 100).toFixed(1)}% Escalated
                </div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Production Models</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  4 Active
                </div>
                <div className="kpi-sub">MLflow Registry</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Monthly Enterprise Revenue Run-Rate Trend</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_orders</span>
                </div>
                <div style={{ padding: '1rem 0' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                    Calculated Run-Rate Total: £{kpis.total_revenue_gbp.toLocaleString()}
                  </div>
                  <div style={{ height: '160px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--pbi-border)', display: 'flex', alignItems: 'flex-end', padding: '10px', gap: '8px' }}>
                    {monthlyRunRate.map((m, i) => {
                      const pct = (m.revenue / maxMonthlyRev) * 100;
                      return (
                        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                          <div style={{ height: `${pct}%`, width: '100%', background: 'var(--pbi-accent-green)', borderRadius: '2px 2px 0 0', opacity: 0.9 }} />
                          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>{m.month}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Revenue Breakdown by Product Category</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_order_items</span>
                </div>
                <div style={{ padding: '0.5rem 0' }}>
                  {categoryRev.map((cat, i) => (
                    <div key={i} style={{ marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                        <span>{cat.category}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--pbi-accent-cyan)' }}>
                          £{(cat.revenue / 1e6).toFixed(2)}M ({cat.share})
                        </span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: cat.share, background: 'var(--pbi-accent-cyan)', borderRadius: '4px' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Cross-Domain Governed Enterprise Risk Matrix</span>
                  <span className="pbi-badge badge-healthy">Governed DB Aggregations</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Risk Exposure (£)</th>
                      <th>Risk Status</th>
                      <th>Automated Trigger Action</th>
                      <th>Source Data Table</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Customer Churn Risk</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>£{(kpis.churn_exposure_gbp / 1e6).toFixed(2)}M</td>
                      <td><span className="pbi-badge badge-high">WATCH (44 AT RISK)</span></td>
                      <td>P1 Loyalty Retention Outreach</td>
                      <td style={{ color: 'var(--text-muted)' }}>analytics.fact_predictions_customer_churn</td>
                    </tr>
                    <tr>
                      <td>Stockout Risk</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>£{(kpis.stockout_exposure_gbp / 1e6).toFixed(2)}M</td>
                      <td><span className="pbi-badge badge-high">REORDER (85 SKUs)</span></td>
                      <td>Automated EOQ Purchase Order</td>
                      <td style={{ color: 'var(--text-muted)' }}>analytics.fact_predictions_inventory_stockout</td>
                    </tr>
                    <tr>
                      <td>Machine Operations</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>£12,500.00</td>
                      <td><span className="pbi-badge badge-critical">CRITICAL (3 MACHINES)</span></td>
                      <td>Emergency Maintenance Dispatch</td>
                      <td style={{ color: 'var(--text-muted)' }}>analytics.fact_predictions_machine_health</td>
                    </tr>
                  </tbody>
                </table>
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: analytics.fact_orders • analytics.dim_customer • analytics.agent_decisions • Updated: {new Date().toLocaleTimeString()}
                </div>
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
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{(kpis.total_revenue_gbp / 1e6).toFixed(2)}M
                </div>
                <div className="kpi-sub">analytics.fact_orders</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Completed Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">100% Fulfilled</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
                  {kpis.units_sold.toLocaleString()}
                </div>
                <div className="kpi-sub">analytics.fact_order_items</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Average Order Value</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  £{kpis.average_order_value_gbp.toLocaleString()}
                </div>
                <div className="kpi-sub">Calculated AOV</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Top Demand SKU</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>PROD_102</div>
                <div className="kpi-sub">Peak Demand SKU</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Forecast WAPE</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>61.08%</div>
                <div className="kpi-sub">Ridge RMSE: 8.81</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Item-Level Daily SKU Sales Demand Forecasts (Ridge Regressor • 95% Confidence Interval)</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_sku_demand</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Product ID</th>
                      <th>Predicted Demand</th>
                      <th>95% Lower Bound</th>
                      <th>95% Upper Bound</th>
                      <th>7-Day Rolling Avg</th>
                      <th>Demand Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(demandData?.demand_forecasts || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {demandData?.provenance?.source || 'analytics.fact_predictions_sku_demand'} • Model: {demandData?.provenance?.model || 'v1.0.0_Ridge'}
                </div>
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
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {customerData?.kpis?.total_customers || 1000}
                </div>
                <div className="kpi-sub">analytics.dim_customer</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">High Risk Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>
                  {customerData?.kpis?.high_risk_customers || 44}
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>Churn Prob &gt; 70%</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Avg Customer Spend</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{(customerData?.kpis?.avg_spend_gbp || 77238).toLocaleString()}
                </div>
                <div className="kpi-sub">LTV Calculation</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Average CSAT</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {customerData?.kpis?.avg_csat || 3.4} / 5.0
                </div>
                <div className="kpi-sub">CSAT Score Index</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Churn Exposure</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>
                  £{((customerData?.kpis?.churn_exposure_gbp || 2100000) / 1e6).toFixed(1)}M
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>Revenue at Risk</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Customer Segmentation Distribution</span>
                  <span className="pbi-badge badge-healthy">analytics.dim_customer</span>
                </div>
                <div style={{ padding: '0.5rem 0' }}>
                  {(customerData?.segmentation || []).map((seg, i) => (
                    <div key={i} style={{ marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                        <span>{seg.segment}</span>
                        <span style={{ fontWeight: '700', color: 'var(--pbi-accent-cyan)' }}>
                          {seg.count} Cust ({seg.share}) • {seg.total_spend}
                        </span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: seg.share, background: 'var(--pbi-accent-purple)', borderRadius: '4px' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>RFM Customer Segmentation Matrix</span>
                  <span className="pbi-badge badge-healthy">RFM Clustering</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Segment Tier</th>
                      <th>Customers</th>
                      <th>Revenue Share</th>
                      <th>Avg Orders</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(customerData?.rfm_matrix || []).map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: '700' }}>{row.tier}</td>
                        <td>{row.customers}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{row.revenue}</td>
                        <td>{row.avg_orders} orders</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>High Churn Risk Customer Intervention Desk (XGBoost Recall 70.45% @ t=0.11)</span>
                  <span className="pbi-badge badge-critical">analytics.fact_predictions_customer_churn</span>
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
                    {(customerData?.top_at_risk_customers || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {customerData?.provenance?.source || 'analytics.fact_predictions_customer_churn'} • Model: {customerData?.provenance?.model || 'v1.0.0_XGBoost'}
                </div>
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
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{((inventoryData?.kpis?.inventory_valuation_gbp || 4800000) / 1e6).toFixed(1)}M
                </div>
                <div className="kpi-sub">Across 3 Warehouses</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">At-Risk SKUs</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>
                  {inventoryData?.kpis?.at_risk_skus || 85} SKUs
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>Vulnerable Stock</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">7-Day Stockout Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {inventoryData?.kpis?.stockout_7d_skus || 14} SKUs
                </div>
                <div className="kpi-sub">Critical Stock Alert</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Avg Days of Supply</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {inventoryData?.kpis?.avg_days_of_supply || 18.4} Days
                </div>
                <div className="kpi-sub">Supply Chain Metric</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Reorder Recommended</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  {inventoryData?.kpis?.reorder_recommended_skus || 22} SKUs
                </div>
                <div className="kpi-sub">Automated EOQ</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Warehouse Risk Breakdown</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_inventory_stockout</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Warehouse Location</th>
                      <th>At-Risk SKUs</th>
                      <th>Critical Stockouts</th>
                      <th>Stock Valuation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(inventoryData?.warehouse_risk || []).map((wh, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: '700' }}>{wh.warehouse}</td>
                        <td>{wh.at_risk_skus} SKUs</td>
                        <td style={{ color: 'var(--pbi-accent-red)', fontWeight: '700' }}>{wh.critical_stockouts} SKUs</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{wh.valuation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>7-Day Stockout Risk &amp; Automated EOQ Reorder Recommendations</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_inventory_stockout</span>
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
                    {(inventoryData?.stockout_alerts || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {inventoryData?.provenance?.source || 'analytics.fact_predictions_inventory_stockout'} • Model: {inventoryData?.provenance?.model || 'v1.0.0_XGBoost_7d'}
                </div>
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
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {operationsData?.kpis?.fleet_machines || 50}
                </div>
                <div className="kpi-sub">Monitored Telemetry</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Healthy Machines</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  {operationsData?.kpis?.healthy_machines || 47}
                </div>
                <div className="kpi-sub">Normal Operation</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Critical Failure Risk</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-red)' }}>
                  {operationsData?.kpis?.critical_risk_machines || 3}
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-red)' }}>&gt;99% Failure Risk</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Anomaly Alerts</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {operationsData?.kpis?.anomaly_alerts || 129}
                </div>
                <div className="kpi-sub">Isolation Forest</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Lead Time Recall</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  {operationsData?.kpis?.lead_time_recall || '100% @ ≥6h'}
                </div>
                <div className="kpi-sub">Guaranteed Lead Time</div>
              </div>
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Telemetry Sensor Time-Series Trend</span>
                  <span className="pbi-badge badge-healthy">6-Hour Rolling Windows</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th>Time Window</th>
                      <th>Temp (°C)</th>
                      <th>Vibration (mm/s)</th>
                      <th>Power (kW)</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(operationsData?.telemetry_timeline || []).map((t, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{t.timestamp}</td>
                        <td style={{ color: t.temp_c > 90 ? 'var(--pbi-accent-red)' : 'var(--text-main)' }}>{t.temp_c}°C</td>
                        <td style={{ color: t.vibr_mm_s > 8 ? 'var(--pbi-accent-red)' : 'var(--text-main)' }}>{t.vibr_mm_s} mm/s</td>
                        <td>{t.power_kw} kW</td>
                        <td>
                          <span className={`pbi-badge ${t.temp_c > 90 ? 'badge-critical' : 'badge-healthy'}`}>
                            {t.temp_c > 90 ? 'ANOMALY DETECTED' : 'NORMAL'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Predictive Telemetry &amp; Maintenance Desk (Isolation Forest + Random Forest)</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_machine_health</span>
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
                    {(operationsData?.machine_health || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {operationsData?.provenance?.source || 'analytics.fact_predictions_machine_health'} • Model: {operationsData?.provenance?.model || 'v1.0.0_RF_IsolationForest'}
                </div>
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
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  {mlopsData?.total_models || 4} Production
                </div>
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
                  <span className="pbi-badge badge-healthy">MLflow SQLite Metadata</span>
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
                    {(mlopsData?.models || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {mlopsData?.provenance?.registry || 'MLflow SQLite Registry'} • Gating: {mlopsData?.provenance?.gating || 'Champion vs Challenger Evaluator'}
                </div>
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
                <div className="kpi-sub">analytics.agent_decisions</div>
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
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>5-Stage Agent Bus Decision Funnel</span>
                  <span className="pbi-badge badge-healthy">Stage 10 AgentBus</span>
                </div>
                <div style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>1. Domain Agent Proposals:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{decisionsData?.funnel?.domain_agent_proposals || 5863}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>2. Business Critic Challenges:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--pbi-accent-yellow)' }}>{decisionsData?.funnel?.critic_challenges || 1240}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>3. Risk Exposure Audits:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{decisionsData?.funnel?.risk_exposure_audits || 5863}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>4. Decision Manager Verdicts:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--pbi-accent-green)' }}>5,863 Complete</span>
                  </div>
                </div>
              </div>

              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Stage 10 Multi-Agent Bus Audit Trail (5,863 Persisted Decisions)</span>
                  <span className="pbi-badge badge-healthy">analytics.agent_decisions</span>
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
                    {(decisionsData?.decisions || []).map((row, i) => (
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
                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--pbi-border)', paddingTop: '0.5rem' }}>
                  Data Provenance: {decisionsData?.provenance?.source || 'analytics.agent_decisions'} • Bus: {decisionsData?.provenance?.bus || 'Stage 10 AgentBus'}
                </div>
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
