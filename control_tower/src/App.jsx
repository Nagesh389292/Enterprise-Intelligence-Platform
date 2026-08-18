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
const CONTROL_TOWER_BUILD = "STAGE13_EXEC_V2";

const COLORS = ['#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];
const RISK_COLORS = {
  'Low Risk': '#10b981',
  'Medium Risk': '#f59e0b',
  'High Risk': '#ef4444',
  'Healthy': '#10b981',
  'Watch': '#f59e0b',
  'Critical': '#ef4444',
  'Approved': '#10b981',
  'Approved w/ Conditions': '#f59e0b',
  'Escalated': '#ef4444'
};

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [showDiagnostics, setShowDiagnostics] = useState(false);

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
  const customerRiskDist = summaryData?.customer_risk_distribution || [];
  const inventoryRiskDist = summaryData?.inventory_risk_distribution || [];
  const machineHealthDist = summaryData?.machine_health_distribution || [];
  const decisionVerdictDist = summaryData?.decision_verdict_distribution || [];
  const riskExposureList = summaryData?.enterprise_risk_exposure || [];
  const actionCenterList = summaryData?.management_action_center || [];

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
              Executive Decision Platform • Multi-Domain Analytics &amp; Governed AI
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {isLoading && <span className="pbi-badge badge-conditions">🔄 RECALCULATING...</span>}
          <button 
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            style={{
              background: showDiagnostics ? 'var(--pbi-accent-blue)' : 'rgba(255,255,255,0.05)',
              border: '1px solid var(--pbi-border)',
              color: '#fff',
              padding: '0.35rem 0.8rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: '600'
            }}
          >
            ⚙ Diagnostics {showDiagnostics ? 'ON' : 'OFF'}
          </button>
          <span className="pbi-badge badge-healthy">● LIVE PIPELINE: OPERATIONAL</span>
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
            {/* ROW 2: 8 EXECUTIVE KPI CARDS */}
            <div className="pbi-kpi-grid">
              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Enterprise Revenue</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{(kpis.total_revenue_gbp / 1e6).toFixed(2)}M
                </div>
                <div className="kpi-sub">Total Governed Orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Total Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">Completed Transactions</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Active Customers</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
                  {kpis.total_customers.toLocaleString()}
                </div>
                <div className="kpi-sub">Registered Enterprise Accounts</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  {kpis.units_sold.toLocaleString()}
                </div>
                <div className="kpi-sub">Fulfilled Inventory Line-Items</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Average Order Value</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
                  £{kpis.average_order_value_gbp.toLocaleString()}
                </div>
                <div className="kpi-sub">Revenue / Total Orders</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Agent Decisions</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_agent_decisions.toLocaleString()}
                </div>
                <div className="kpi-sub">Stage 10 AgentBus Audit Trail</div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Escalated Risk Rate</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {((kpis.escalated_decisions_count / kpis.total_agent_decisions) * 100).toFixed(1)}%
                </div>
                <div className="kpi-sub" style={{ color: 'var(--pbi-accent-yellow)' }}>
                  {kpis.escalated_decisions_count} Human Reviews Needed
                </div>
              </div>

              <div className="pbi-kpi-card">
                <div className="kpi-title">Production Models</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
                  4 Active
                </div>
                <div className="kpi-sub">MLflow Monitored Champion Models</div>
              </div>
            </div>

            {/* ROW 3: REVENUE TREND & CATEGORY REVENUE */}
            <div className="pbi-visuals-grid">
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Monthly Enterprise Revenue Run-Rate Trend</span>
                  <span className="pbi-badge badge-healthy">YTD Run-Rate</span>
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
                        <Tooltip formatter={(v) => [`£${v.toLocaleString()}`, 'Revenue']} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Area type="monotone" dataKey="revenue" stroke="#10b981" fillOpacity={1} fill="url(#colorRev)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No revenue trend data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Revenue Breakdown by Product Category</span>
                  <span className="pbi-badge badge-healthy">Product Share</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {categoryRev.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={categoryRev} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${(v/1e6).toFixed(1)}M`} />
                        <YAxis type="category" dataKey="category" stroke="#94a3b8" fontSize={10} width={130} />
                        <Tooltip formatter={(v) => [`£${(v/1e6).toFixed(2)}M`, 'Revenue']} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Bar dataKey="revenue" fill="#06b6d4" radius={[0, 4, 4, 0]}>
                          {categoryRev.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No category data</div>}
                </div>
              </div>

              {/* ROW 4: ORDERS & UNITS TREND & AVERAGE ORDER VALUE */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Monthly Orders &amp; Units Sold Volume Trend</span>
                  <span className="pbi-badge badge-healthy">Fulfillment Volume</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {monthlyRunRate.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={monthlyRunRate}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                        <YAxis yAxisId="left" stroke="#3b82f6" fontSize={11} label={{ value: 'Orders', angle: -90, position: 'insideLeft', fill: '#3b82f6', fontSize: 10 }} />
                        <YAxis yAxisId="right" orientation="right" stroke="#8b5cf6" fontSize={11} label={{ value: 'Units', angle: 90, position: 'insideRight', fill: '#8b5cf6', fontSize: 10 }} />
                        <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Bar yAxisId="left" dataKey="orders" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                        <Line yAxisId="right" type="monotone" dataKey="units" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No volume data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Average Order Value (AOV) Trend</span>
                  <span className="pbi-badge badge-healthy">Monetization Efficiency</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {monthlyRunRate.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={monthlyRunRate}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} />
                        <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${v}`} />
                        <Tooltip formatter={(v) => [`£${v.toLocaleString()}`, 'AOV']} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Line type="monotone" dataKey="aov" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No AOV trend data</div>}
                </div>
              </div>

              {/* ROW 5: CUSTOMER RISK DISTRIBUTION & SCATTER PLOT */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Customer Churn Risk Tier Distribution</span>
                  <span className="pbi-badge badge-critical">XGBoost Churn Classifier</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem', display: 'flex', alignItems: 'center' }}>
                  {customerRiskDist.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={customerRiskDist} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                          {customerRiskDist.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v, name) => [`${v} Customers`, name]} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Legend verticalAlign="bottom" height={36} iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No customer risk data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Customer Revenue Spend vs. Churn Risk Probability</span>
                  <span className="pbi-badge badge-critical">High LTV at Risk</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {(customerData?.top_at_risk_customers || []).length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <ScatterChart>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" dataKey="total_revenue" name="Total Spend" stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${(v/1e3).toFixed(0)}k`} />
                        <YAxis type="number" dataKey="churn_probability" name="Churn Risk" stroke="#94a3b8" fontSize={11} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(v, name) => [name === 'Total Spend' ? `£${v.toLocaleString()}` : `${(v*100).toFixed(1)}%`, name]} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Scatter name="Customers" data={customerData?.top_at_risk_customers || []} fill="#ef4444" />
                      </ScatterChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No customer scatter data</div>}
                </div>
              </div>

              {/* ROW 6: INVENTORY RISK & MACHINE HEALTH DISTRIBUTION */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Warehouse Inventory Risk Classification</span>
                  <span className="pbi-badge badge-healthy">XGBoost 7-Day Model</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {inventoryRiskDist.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={inventoryRiskDist} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value">
                          {inventoryRiskDist.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v, name) => [`${v} SKUs`, name]} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Legend verticalAlign="bottom" height={36} iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No inventory risk data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Machine Telemetry Fleet Health Status</span>
                  <span className="pbi-badge badge-critical">RF + Isolation Forest</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {machineHealthDist.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={machineHealthDist} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value">
                          {machineHealthDist.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v, name) => [`${v} Machines`, name]} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Legend verticalAlign="bottom" height={36} iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No machine health data</div>}
                </div>
              </div>

              {/* ROW 7: ENTERPRISE RISK EXPOSURE & MANAGEMENT ACTION CENTER */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Cross-Domain Financial Risk Exposure (£)</span>
                  <span className="pbi-badge badge-critical">Quantified Risk</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {riskExposureList.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={riskExposureList} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" stroke="#94a3b8" fontSize={11} tickFormatter={v => `£${(v/1e6).toFixed(2)}M`} />
                        <YAxis type="category" dataKey="domain" stroke="#94a3b8" fontSize={10} width={130} />
                        <Tooltip formatter={(v) => [`£${v.toLocaleString()}`, 'Exposure (£)']} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Bar dataKey="exposure" fill="#ef4444" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No risk exposure data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>🚨 MANAGEMENT ACTION CENTER (Top Real-Time Database Action Items)</span>
                  <span className="pbi-badge badge-critical">Action Items</span>
                </div>
                <div style={{ padding: '0.5rem 0' }}>
                  {actionCenterList.map((act, i) => (
                    <div key={i} style={{ marginBottom: '0.75rem', padding: '0.6rem', background: 'rgba(255,255,255,0.02)', borderLeft: `3px solid ${act.severity === 'CRITICAL' ? 'var(--pbi-accent-red)' : act.severity === 'HIGH' ? 'var(--pbi-accent-yellow)' : 'var(--pbi-accent-cyan)'}`, borderRadius: '0 4px 4px 0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '700', marginBottom: '0.2rem' }}>
                        <span>{act.title}</span>
                        <span style={{ color: act.severity === 'CRITICAL' ? 'var(--pbi-accent-red)' : 'var(--pbi-accent-yellow)' }}>{act.exposure}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>→ Recommended Action: {act.recommended_action}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ROW 8: AI DECISION SUMMARY & 5-STAGE BUS ARCHITECTURE */}
              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>Stage 10 AgentBus Decision Verdict Distribution</span>
                  <span className="pbi-badge badge-healthy">5,863 AI Decisions</span>
                </div>
                <div style={{ width: '100%', height: '220px', paddingTop: '0.5rem' }}>
                  {decisionVerdictDist.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={decisionVerdictDist} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value">
                          {decisionVerdictDist.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v, name) => [`${v} Decisions`, name]} contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                        <Legend verticalAlign="bottom" height={36} iconType="circle" />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <div className="no-data">No decision data</div>}
                </div>
              </div>

              <div className="pbi-visual-card">
                <div className="visual-header">
                  <span>5-Stage Collaborative Agent Hierarchy Execution Bus</span>
                  <span className="pbi-badge badge-healthy">Stage 10 Architecture</span>
                </div>
                <div style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>1. Domain Agent Proposals:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>5,863 Proposals</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>2. Business Critic Challenges:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--pbi-accent-yellow)' }}>1,240 Revised</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>3. Risk Exposure Audits:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>5,863 Audited</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span>4. Decision Manager Verdicts:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--pbi-accent-green)' }}>5,863 Complete</span>
                  </div>
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
                <div className="kpi-sub">Total Governed Revenue</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Completed Orders</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
                  {kpis.total_orders.toLocaleString()}
                </div>
                <div className="kpi-sub">100% Order Fulfillment</div>
              </div>
              <div className="pbi-kpi-card">
                <div className="kpi-title">Units Sold</div>
                <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
                  {kpis.units_sold.toLocaleString()}
                </div>
                <div className="kpi-sub">Inventory Line Items</div>
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

        {/* COLLAPSIBLE DIAGNOSTICS DRAWER (TOGGLED VIA HEADER BUTTON) */}
        {showDiagnostics && (
          <div style={{ marginTop: '2rem', padding: '1rem', background: '#090d16', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#94a3b8' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: '#38bdf8', fontWeight: 'bold' }}>
              <span>⚙️ DEVELOPER DIAGNOSTICS DRAWER</span>
              <span>BUILD: {CONTROL_TOWER_BUILD}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
              <div>
                <div style={{ color: '#fff', marginBottom: '0.2rem' }}>SLICER PARAMETERS:</div>
                <div>Date: {dateRange}</div>
                <div>Region: {region}</div>
                <div>Warehouse: {warehouse}</div>
                <div>Category: {category}</div>
                <div>Segment: {segment}</div>
              </div>
              <div>
                <div style={{ color: '#fff', marginBottom: '0.2rem' }}>FASTAPI TELEMETRY:</div>
                <div>Last Query: ?{lastQueryStr}</div>
                <div>HTTP Status: {lastHttpStatus}</div>
                <div>API Error: {apiError || "None"}</div>
              </div>
              <div>
                <div style={{ color: '#fff', marginBottom: '0.2rem' }}>DATA CONTRACT AUDIT:</div>
                <div>Revenue: £{kpis.total_revenue_gbp.toLocaleString()}</div>
                <div>Monthly Run-Rate Rows: {monthlyRunRate.length}</div>
                <div>Category Revenue Rows: {categoryRev.length}</div>
                <div>SQL Table Source: analytics.fact_orders</div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
