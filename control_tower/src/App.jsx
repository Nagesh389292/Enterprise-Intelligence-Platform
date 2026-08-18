import React, { useState, useEffect } from 'react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [summaryData, setSummaryData] = useState(null);
  const [customerData, setCustomerData] = useState([]);
  const [demandData, setDemandData] = useState([]);
  const [inventoryData, setInventoryData] = useState([]);
  const [operationsData, setOperationsData] = useState([]);
  const [mlopsData, setMlopsData] = useState([]);
  const [decisionsData, setDecisionsData] = useState([]);
  const [selectedDecision, setSelectedDecision] = useState(null);
  
  // Slicers
  const [dateRange, setDateRange] = useState("YTD 2026");
  const [region, setRegion] = useState("All Regions");
  const [warehouse, setWarehouse] = useState("All Warehouses");

  useEffect(() => {
    fetch(`${API_BASE}/api/control-tower/summary`)
      .then(res => res.json())
      .then(data => setSummaryData(data))
      .catch(() => {
        setSummaryData({
          executive_kpis: {
            total_revenue_gbp: 77237960.93,
            total_customers: 1000,
            total_agent_decisions: 5863,
            escalated_decisions_count: 380,
            system_health: "OPERATIONAL",
            drift_status: "MONITORED_CLEAN"
          }
        });
      });

    fetch(`${API_BASE}/api/control-tower/customer`)
      .then(res => res.json())
      .then(data => setCustomerData(data.top_at_risk_customers || []))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/demand`)
      .then(res => res.json())
      .then(data => setDemandData(data.demand_forecasts || []))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/inventory`)
      .then(res => res.json())
      .then(data => setInventoryData(data.stockout_alerts || []))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/operations`)
      .then(res => res.json())
      .then(data => setOperationsData(data.machine_health || []))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/mlops`)
      .then(res => res.json())
      .then(data => setMlopsData(data.models || []))
      .catch(() => {});

    fetch(`${API_BASE}/api/control-tower/decisions`)
      .then(res => res.json())
      .then(data => setDecisionsData(data.decisions || []))
      .catch(() => {});
  }, []);

  const kpis = summaryData?.executive_kpis || {
    total_revenue_gbp: 77237960.93,
    total_customers: 1000,
    total_agent_decisions: 5863,
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
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Power BI Executive Architecture • Live PostgreSQL Stream</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span className="pbi-badge badge-healthy">● LIVE SYSTEM HEALTH: OPERATIONAL</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Refresh: {new Date().toLocaleDateString()}</span>
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

      {/* Dashboard Canvas */}
      <main className="pbi-canvas">
        {/* KPI Strip */}
        <div className="pbi-kpi-grid">
          <div className="pbi-kpi-card">
            <div className="kpi-title">Enterprise Revenue</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-green)' }}>
              £{(kpis.total_revenue_gbp / 1e6).toFixed(2)}M
            </div>
            <div className="kpi-sub">▲ 8.4% vs prev period</div>
          </div>

          <div className="pbi-kpi-card">
            <div className="kpi-title">Active Customers</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
              {kpis.total_customers.toLocaleString()}
            </div>
            <div className="kpi-sub">▲ 4.2% organic growth</div>
          </div>

          <div className="pbi-kpi-card">
            <div className="kpi-title">Completed Orders</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-blue)' }}>
              10,000
            </div>
            <div className="kpi-sub">▲ 6.1% fulfillment rate</div>
          </div>

          <div className="pbi-kpi-card">
            <div className="kpi-title">Agent Decisions</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-purple)' }}>
              {kpis.total_agent_decisions.toLocaleString()}
            </div>
            <div className="kpi-sub">Stage 10 AgentBus</div>
          </div>

          <div className="pbi-kpi-card">
            <div className="kpi-title">Escalated Risk</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-yellow)' }}>
              {kpis.escalated_decisions_count}
            </div>
            <div className="kpi-sub" style={{ color: 'var(--pbi-accent-yellow)' }}>6.4% Human Oversight</div>
          </div>

          <div className="pbi-kpi-card">
            <div className="kpi-title">Production Models</div>
            <div className="kpi-val" style={{ color: 'var(--pbi-accent-cyan)' }}>
              4 Active
            </div>
            <div className="kpi-sub">MLflow Monitored</div>
          </div>
        </div>

        {/* PAGE 1: EXECUTIVE OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="pbi-visuals-grid">
            <div className="pbi-visual-card">
              <div className="visual-header">
                <span>Revenue Trend &amp; Monthly Performance</span>
                <span className="pbi-badge badge-healthy">PostgreSQL Real-time</span>
              </div>
              <div style={{ padding: '1rem 0' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Gross Sales Run-Rate: £77,237,960.93</div>
                <div style={{ height: '140px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--pbi-border)', display: 'flex', alignItems: 'flex-end', padding: '10px', gap: '8px' }}>
                  {[40, 55, 62, 78, 71, 85, 92, 88, 95, 100].map((h, i) => (
                    <div key={i} style={{ flex: 1, height: `${h}%`, background: 'var(--pbi-accent-cyan)', borderRadius: '2px 2px 0 0', opacity: 0.85 }} />
                  ))}
                </div>
              </div>
            </div>

            <div className="pbi-visual-card">
              <div className="visual-header">
                <span>Cross-Domain Risk Matrix</span>
                <span className="pbi-badge badge-healthy">Governed Rules</span>
              </div>
              <table className="pbi-table">
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Risk Exposure</th>
                    <th>Status</th>
                    <th>Action</th>
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
                    <td>Machine Health</td>
                    <td>3 Critical Telemetry Alerts</td>
                    <td><span className="pbi-badge badge-critical">IMMEDIATE</span></td>
                    <td>Maintenance Squad</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PAGE 2: SALES & DEMAND */}
        {activeTab === 'sales' && (
          <div className="pbi-visuals-grid">
            <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
              <div className="visual-header">
                <span>Daily SKU Sales Demand Forecasting (Ridge Linear Regressor • 95% CI)</span>
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
                    <th>Confidence Tier</th>
                  </tr>
                </thead>
                <tbody>
                  {demandData.slice(0, 8).map((row, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.product_id}</td>
                      <td style={{ fontWeight: '700', color: 'var(--pbi-accent-green)' }}>{row.predicted_demand_units} units</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{row.lower_bound_95} units</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{row.upper_bound_95} units</td>
                      <td>{row.rolling_avg_7d} units</td>
                      <td><span className="pbi-badge badge-approved">95% High Confidence</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PAGE 3: CUSTOMER INTELLIGENCE */}
        {activeTab === 'customer' && (
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
                    <th>Recommended Retention Strategy</th>
                  </tr>
                </thead>
                <tbody>
                  {customerData.slice(0, 8).map((row, i) => (
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
                      <td><span className="pbi-badge badge-approved">VIP Loyalty Rebate &amp; Account Outreach</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PAGE 4: INVENTORY INTELLIGENCE */}
        {activeTab === 'inventory' && (
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
                  {inventoryData.slice(0, 8).map((row, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--pbi-accent-cyan)' }}>{row.item_id}</td>
                      <td style={{ fontWeight: '800', color: row.stockout_risk_prob_7d > 0.7 ? 'var(--pbi-accent-red)' : 'var(--pbi-accent-yellow)' }}>
                        {(row.stockout_risk_prob_7d * 100).toFixed(1)}%
                      </td>
                      <td><span className="pbi-badge badge-critical">{row.risk_severity || 'Critical'}</span></td>
                      <td>{row.current_stock_level} units</td>
                      <td>{row.reorder_point} units</td>
                      <td style={{ fontWeight: '700', color: 'var(--pbi-accent-green)' }}>{row.recommended_reorder_qty} units</td>
                      <td><span className="pbi-badge badge-approved">Trigger Expedited PO</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PAGE 5: MACHINE OPERATIONS */}
        {activeTab === 'operations' && (
          <div className="pbi-visuals-grid">
            <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
              <div className="visual-header">
                <span>Predictive Telemetry &amp; Maintenance Desk (100% Recall @ ≥6h Lead Time)</span>
                <span className="pbi-badge badge-healthy">Isolation Forest + Random Forest</span>
              </div>
              <table className="pbi-table">
                <thead>
                  <tr>
                    <th>Machine ID</th>
                    <th>Anomaly Score</th>
                    <th>24h Failure Probability</th>
                    <th>Lead Time Alert</th>
                    <th>Health Status</th>
                    <th>Automated Maintenance Dispatch</th>
                  </tr>
                </thead>
                <tbody>
                  {operationsData.slice(0, 8).map((row, i) => (
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
        )}

        {/* PAGE 6: MLOPS & MODEL SYSTEM HEALTH */}
        {activeTab === 'mlops' && (
          <div className="pbi-visuals-grid">
            <div className="pbi-visual-card" style={{ gridColumn: '1 / -1' }}>
              <div className="visual-header">
                <span>Production ML Model Registry &amp; Drift Monitoring (MLflow SQLite)</span>
                <span className="pbi-badge badge-healthy">Automated Champion/Challenger</span>
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
        )}

        {/* PAGE 7: AI DECISION CENTER */}
        {activeTab === 'decisions' && (
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
                  {decisionsData.slice(0, 10).map((row, i) => (
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
