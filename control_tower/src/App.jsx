import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ScatterChart,
  Scatter,
  ComposedChart
} from 'recharts';

const API_BASE = "http://localhost:8000";
const CONTROL_TOWER_BUILD = "STAGE13_DEBUG_001";

const COLORS = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");

  // Dynamic Filter Options from API
  const [filterOptions, setFilterOptions] = useState({
    regions: ["All Regions", "UK North", "UK South", "EMEA"],
    warehouses: ["All Warehouses", "WH-001 (London Central)", "WH-002 (Manchester)", "WH-003 (Birmingham)"],
    categories: ["All Categories", "Industrial Equipment", "Electronics", "Components"],
    customer_segments: ["All Customer Segments", "Enterprise VIP", "Mid-Market", "SMB"],
    date_periods: ["YTD 2026", "Q3 2026", "Q2 2026", "Q1 2026"]
  });

  // Global Filter State
  const [dateRange, setDateRange] = useState("YTD 2026");
  const [region, setRegion] = useState("All Regions");
  const [warehouse, setWarehouse] = useState("All Warehouses");
  const [category, setCategory] = useState("All Categories");
  const [segment, setSegment] = useState("All Customer Segments");

  // Data States
  const [summaryData, setSummaryData] = useState(null);
  const [customerData, setCustomerData] = useState(null);
  const [demandData, setDemandData] = useState(null);
  const [inventoryData, setInventoryData] = useState(null);
  const [operationsData, setOperationsData] = useState(null);
  const [mlopsData, setMlopsData] = useState(null);
  const [decisionsData, setDecisionsData] = useState(null);

  // Debug & Network Tracking State
  const [lastQueryStr, setLastQueryStr] = useState("");
  const [lastHttpStatus, setLastHttpStatus] = useState(200);
  const [apiError, setApiError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [sortField, setSortField] = useState(null);
  const [sortAsc, setSortAsc] = useState(true);

  // Fetch filter options on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/control-tower/filter-options`)
      .then(res => res.json())
      .then(data => {
        if (data && data.regions) setFilterOptions(data);
      })
      .catch(() => {});
  }, []);

  // Shared Query Parameter Builder
  const buildQueryParams = () => {
    return new URLSearchParams({
      date_period: dateRange,
      region: region,
      warehouse: warehouse,
      category: category,
      customer_segment: segment
    }).toString();
  };

  // Reset All Filters function
  const handleResetFilters = () => {
    setDateRange("YTD 2026");
    setRegion("All Regions");
    setWarehouse("All Warehouses");
    setCategory("All Categories");
    setSegment("All Customer Segments");
  };

  // Fetch filtered data whenever slicers change
  useEffect(() => {
    setIsLoading(true);
    setApiError(null);
    const queryStr = buildQueryParams();
    setLastQueryStr(queryStr);

    Promise.all([
      fetch(`${API_BASE}/api/control-tower/summary?${queryStr}`),
      fetch(`${API_BASE}/api/control-tower/customer?${queryStr}`),
      fetch(`${API_BASE}/api/control-tower/demand?${queryStr}`),
      fetch(`${API_BASE}/api/control-tower/inventory?${queryStr}`),
      fetch(`${API_BASE}/api/control-tower/operations`),
      fetch(`${API_BASE}/api/control-tower/mlops`),
      fetch(`${API_BASE}/api/control-tower/decisions`),
    ])
      .then(async ([sumRes, custRes, demRes, invRes, opsRes, mlRes, decRes]) => {
        setLastHttpStatus(sumRes.status);
        if (!sumRes.ok) throw new Error(`HTTP Error ${sumRes.status}`);

        const summary = await sumRes.json();
        const customer = await custRes.json();
        const demand = await demRes.json();
        const inventory = await invRes.json();
        const ops = await opsRes.json();
        const mlops = await mlRes.json();
        const decisions = await decRes.json();

        setSummaryData(summary);
        setCustomerData(customer);
        setDemandData(demand);
        setInventoryData(inventory);
        setOperationsData(ops);
        setMlopsData(mlops);
        setDecisionsData(decisions);
        setIsLoading(false);
      })
      .catch(err => {
        setApiError(err.message || "Failed to fetch Control Tower data");
        setIsLoading(false);
      });
  }, [dateRange, region, warehouse, category, segment]);

  // Derived KPI calculations from active summary API
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

  const monthlyRunRate = summaryData?.monthly_run_rate || [];
  const categoryRev = summaryData?.category_revenue || [];

  // Sorting helper
  const handleSort = (field) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(true); }
  };

  const sortRecords = (records) => {
    if (!sortField || !records) return records || [];
    return [...records].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];
      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  };

  return (
    <div className="pbi-app">
      {/* Power BI Top Header */}
      <header className="pbi-top-header">
        <div className="pbi-brand">
          <div className="pbi-logo">N</div>
          <div>
            <div className="pbi-title">NexaCore Enterprise Intelligence Control Tower</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Power BI Analytical Engine • Recharts Visualizations • {CONTROL_TOWER_BUILD}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {isLoading && <span className="pbi-badge badge-conditions">🔄 RECALCULATING SQL...</span>}
          <span className="pbi-badge badge-healthy">● LIVE PIPELINE: OPERATIONAL</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Refreshed: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* Global Slicers Bar */}
      <div className="pbi-slicers-bar">
        <div className="slicer-group">
          <span>Date Period:</span>
          <select value={dateRange} onChange={e => setDateRange(e.target.value)} className="slicer-select">
            {filterOptions.date_periods.map((op, i) => <option key={i} value={op}>{op}</option>)}
          </select>
        </div>

        <div className="slicer-group">
          <span>Region:</span>
          <select value={region} onChange={e => setRegion(e.target.value)} className="slicer-select">
            {filterOptions.regions.map((op, i) => <option key={i} value={op}>{op}</option>)}
          </select>
        </div>

        <div className="slicer-group">
          <span>Warehouse:</span>
          <select value={warehouse} onChange={e => setWarehouse(e.target.value)} className="slicer-select">
            {filterOptions.warehouses.map((op, i) => <option key={i} value={op}>{op}</option>)}
          </select>
        </div>

        <div className="slicer-group">
          <span>Category:</span>
          <select value={category} onChange={e => setCategory(e.target.value)} className="slicer-select">
            {filterOptions.categories.map((op, i) => <option key={i} value={op}>{op}</option>)}
          </select>
        </div>

        <div className="slicer-group">
          <span>Customer Segment:</span>
          <select value={segment} onChange={e => setSegment(e.target.value)} className="slicer-select">
            {filterOptions.customer_segments.map((op, i) => <option key={i} value={op}>{op}</option>)}
          </select>
        </div>

        <button 
          onClick={handleResetFilters}
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: 'var(--pbi-accent-red)',
            padding: '0.4rem 0.8rem',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: '700'
          }}
        >
          RESET ALL FILTERS
        </button>
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

      {/* API Error Notification */}
      {apiError && (
        <div style={{ background: 'rgba(239,68,68,0.2)', border: '1px solid var(--pbi-accent-red)', color: '#fca5a5', padding: '0.75rem 1.5rem', margin: '1rem', borderRadius: '6px' }}>
          ⚠️ <strong>API Data Flow Alert:</strong> {apiError}. Unable to populate visualizations.
        </div>
      )}

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
                <div className="kpi-sub">Source: analytics.fact_orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">Source: analytics.fact_orders</div>
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
                <div className="kpi-sub">Source: analytics.fact_order_items</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Average Order Value</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{kpis.average_order_value_gbp.toLocaleString()}
                </div>
                <div className="kpi-sub">Formula: Revenue / Orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Agent Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_agent_decisions.toLocaleString()}
                </div>
                <div className="kpi-sub">Source: analytics.agent_decisions</div>
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
              {/* Visual 1: Recharts AreaChart */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Monthly Enterprise Revenue Run-Rate Trend</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_orders</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {monthlyRunRate.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={monthlyRunRate}>
                        <defs>
                          <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                        <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${(v/1e6).toFixed(1)}M`} />
                        <Tooltip 
                          formatter={(v) => [`£${v.toLocaleString()}`, 'Revenue']}
                          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '4px' }} 
                        />
                        <Area type="monotone" dataKey="revenue" stroke="#10b981" fillOpacity={1} fill="url(#colorRev)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: '80px' }}>No revenue trend data returned from API</div>
                  )}
                </div>
              </div>

              {/* Visual 2: Recharts BarChart */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Revenue Breakdown by Product Category</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_order_items</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {categoryRev.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={categoryRev} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${(v/1e6).toFixed(1)}M`} />
                        <YAxis type="category" dataKey="category" stroke="#94a3b8" fontSize={10} width={130} />
                        <Tooltip 
                          formatter={(v) => [`£${(v/1e6).toFixed(2)}M`, 'Category Revenue']}
                          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '4px' }} 
                        />
                        <Bar dataKey="revenue" fill="#06b6d4" radius={[0, 4, 4, 0]}>
                          {categoryRev.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: '80px' }}>No category data returned from API</div>
                  )}
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
                  Data Provenance: analytics.fact_orders • analytics.dim_customer • analytics.agent_decisions • Filter Query: {lastQueryStr}
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
                      <th onClick={() => handleSort('product_id')} style={{ cursor: 'pointer' }}>Product ID ↕</th>
                      <th onClick={() => handleSort('predicted_demand_units')} style={{ cursor: 'pointer' }}>Predicted Demand ↕</th>
                      <th>95% Lower Bound</th>
                      <th>95% Upper Bound</th>
                      <th>7-Day Rolling Avg</th>
                      <th>Demand Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRecords(demandData?.demand_forecasts || []).map((row, i) => (
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
            </div>

            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>High Churn Risk Customer Intervention Desk</span>
                  <span className="pbi-badge badge-critical">analytics.fact_predictions_customer_churn</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('customer_id')} style={{ cursor: 'pointer' }}>Customer ID ↕</th>
                      <th onClick={() => handleSort('churn_probability')} style={{ cursor: 'pointer' }}>Churn Probability ↕</th>
                      <th>Risk Tier</th>
                      <th onClick={() => handleSort('total_revenue')} style={{ cursor: 'pointer' }}>Total Spend ↕</th>
                      <th>Days Inactive</th>
                      <th>CSAT Score</th>
                      <th>Recommended Retention Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRecords(customerData?.top_at_risk_customers || []).map((row, i) => (
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
            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>7-Day Stockout Risk &amp; Automated EOQ Reorder Recommendations</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_inventory_stockout</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('item_id')} style={{ cursor: 'pointer' }}>Item ID ↕</th>
                      <th onClick={() => handleSort('stockout_risk_prob_7d')} style={{ cursor: 'pointer' }}>7-Day Stockout Risk ↕</th>
                      <th>Risk Severity</th>
                      <th>Current Stock</th>
                      <th>Reorder Point</th>
                      <th>Recommended Reorder Qty</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRecords(inventoryData?.stockout_alerts || []).map((row, i) => (
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
            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Predictive Telemetry &amp; Maintenance Desk</span>
                  <span className="pbi-badge badge-healthy">analytics.fact_predictions_machine_health</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('machine_id')} style={{ cursor: 'pointer' }}>Machine ID ↕</th>
                      <th onClick={() => handleSort('anomaly_score')} style={{ cursor: 'pointer' }}>Anomaly Score ↕</th>
                      <th onClick={() => handleSort('failure_prob_24h')} style={{ cursor: 'pointer' }}>24h Failure Probability ↕</th>
                      <th>Lead Time Alert</th>
                      <th>Health Status</th>
                      <th>Maintenance Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRecords(operationsData?.machine_health || []).map((row, i) => (
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
            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Production Model Registry &amp; Drift Monitoring</span>
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
              </div>
            </div>
          </>
        )}

        {/* PAGE 7: AI DECISION CENTER */}
        {activeTab === 'decisions' && (
          <>
            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
                <div className="visual-header">
                  <span>Stage 10 Multi-Agent Bus Audit Trail (5,863 Persisted Decisions)</span>
                  <span className="pbi-badge badge-healthy">analytics.agent_decisions</span>
                </div>
                <table className="pbi-table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('decision_id')} style={{ cursor: 'pointer' }}>Decision ID ↕</th>
                      <th>Domain</th>
                      <th>Entity ID</th>
                      <th>Proposed Action</th>
                      <th onClick={() => handleSort('financial_exposure_gbp')} style={{ cursor: 'pointer' }}>Exposure (£) ↕</th>
                      <th>Risk Level</th>
                      <th>Final Verdict</th>
                      <th>Reasoning Chain</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortRecords(decisionsData?.decisions || []).map((row, i) => (
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

        {/* TEMPORARY STAGE 13 DIAGNOSTIC DEBUG PANEL */}
        <div style={{ marginTop: '2rem', padding: '1rem', background: '#090d16', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#94a3b8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: '#38bdf8', fontWeight: 'bold' }}>
            <span>🛠️ CONTROL TOWER DIAGNOSTIC DEBUG PANEL</span>
            <span>BUILD: {CONTROL_TOWER_BUILD}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
            <div>
              <div style={{ color: '#fff', marginBottom: '0.2rem' }}>CURRENT FILTERS:</div>
              <div>Date: {dateRange}</div>
              <div>Region: {region}</div>
              <div>Warehouse: {warehouse}</div>
              <div>Category: {category}</div>
              <div>Segment: {segment}</div>
            </div>
            <div>
              <div style={{ color: '#fff', marginBottom: '0.2rem' }}>NETWORK TELEMETRY:</div>
              <div>Last Query: ?{lastQueryStr}</div>
              <div>HTTP Status: {lastHttpStatus}</div>
              <div>API Error: {apiError || "None"}</div>
            </div>
            <div>
              <div style={{ color: '#fff', marginBottom: '0.2rem' }}>DATA CONTRACT COUNTS:</div>
              <div>Revenue: £{kpis.total_revenue_gbp.toLocaleString()}</div>
              <div>Monthly Run-Rate Rows: {monthlyRunRate.length}</div>
              <div>Category Revenue Rows: {categoryRev.length}</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
