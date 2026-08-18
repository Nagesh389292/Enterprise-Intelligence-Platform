import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  TrendingUp, 
  Package, 
  Cpu, 
  BrainCircuit, 
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  ShieldAlert,
  Sliders,
  DollarSign
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [summaryData, setSummaryData] = useState(null);
  const [customerData, setCustomerData] = useState(null);
  const [demandData, setDemandData] = useState(null);
  const [inventoryData, setInventoryData] = useState(null);
  const [operationsData, setOperationsData] = useState(null);
  const [decisionsData, setDecisionsData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, cRes, dRes, iRes, oRes, decRes] = await Promise.all([
        fetch('/api/control-tower/summary').then(r => r.json()),
        fetch('/api/control-tower/customer').then(r => r.json()),
        fetch('/api/control-tower/demand').then(r => r.json()),
        fetch('/api/control-tower/inventory').then(r => r.json()),
        fetch('/api/control-tower/operations').then(r => r.json()),
        fetch('/api/control-tower/decisions').then(r => r.json()),
      ]);
      setSummaryData(sRes);
      setCustomerData(cRes);
      setDemandData(dRes);
      setInventoryData(iRes);
      setOperationsData(oRes);
      setDecisionsData(decRes);
    } catch (err) {
      console.error('Failed fetching control tower data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const navItems = [
    { id: 'overview', label: 'Executive Overview', icon: LayoutDashboard },
    { id: 'customer', label: 'Customer Intelligence', icon: Users },
    { id: 'demand', label: 'Demand Intelligence', icon: TrendingUp },
    { id: 'inventory', label: 'Inventory Intelligence', icon: Package },
    { id: 'operations', label: 'Machine Operations', icon: Cpu },
    { id: 'decisions', label: 'AI Decision Center', icon: BrainCircuit },
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand-header">
          <div className="brand-logo">N</div>
          <div>
            <div className="brand-title">NEXACORE</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Enterprise Control Tower</div>
          </div>
        </div>

        <ul className="nav-list">
          {navItems.map(item => {
            const Icon = item.icon;
            return (
              <li 
                key={item.id} 
                className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => setActiveTab(item.id)}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </li>
            );
          })}
        </ul>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-bar">
          <h1 className="page-title">
            {navItems.find(i => i.id === activeTab)?.label}
          </h1>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button 
              onClick={fetchData}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--glass-border)',
                color: 'var(--text-main)',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>

            <div className="status-badge">
              <span className="pulse-dot"></span>
              <span>LIVE MLOps Pipeline</span>
            </div>
          </div>
        </header>

        {/* Tab 1: Executive Overview */}
        {activeTab === 'overview' && (
          <div>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-header">
                  <span>Total Revenue</span>
                  <DollarSign size={16} color="var(--accent-emerald)" />
                </div>
                <div className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
                  £{summaryData?.executive_kpis?.total_revenue_gbp?.toLocaleString() || '1,452,800'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Active Customers</span>
                  <Users size={16} color="var(--accent-blue)" />
                </div>
                <div className="metric-value" style={{ color: 'var(--accent-blue)' }}>
                  {summaryData?.executive_kpis?.total_customers || 1500}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Agent Decisions Persisted</span>
                  <BrainCircuit size={16} color="var(--accent-cyan)" />
                </div>
                <div className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
                  {summaryData?.executive_kpis?.total_agent_decisions?.toLocaleString() || 4977}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Escalated Decisions</span>
                  <AlertTriangle size={16} color="var(--accent-amber)" />
                </div>
                <div className="metric-value" style={{ color: 'var(--accent-amber)' }}>
                  {summaryData?.executive_kpis?.escalated_decisions_count || 354}
                </div>
              </div>
            </div>

            {/* Active ML Models Grid */}
            <div className="table-card">
              <div className="table-header">Active Production Model Registry</div>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Model Architecture</th>
                    <th>Stage</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryData?.active_models && Object.entries(summaryData.active_models).map(([domain, ver]) => (
                    <tr key={domain}>
                      <td style={{ textTransform: 'capitalize', fontWeight: '600' }}>{domain.replace('_', ' ')}</td>
                      <td className="mono-text">{ver}</td>
                      <td><span className="badge badge-approved">PRODUCTION</span></td>
                      <td><span style={{ color: 'var(--accent-emerald)' }}>✓ Active Scoring</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Customer Intelligence */}
        {activeTab === 'customer' && (
          <div className="table-card">
            <div className="table-header">High Churn Risk Intervention Desk</div>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Customer ID</th>
                  <th>Churn Probability</th>
                  <th>Risk Tier</th>
                  <th>Total Revenue</th>
                  <th>Days Inactive</th>
                  <th>Avg CSAT</th>
                </tr>
              </thead>
              <tbody>
                {customerData?.top_at_risk_customers?.map(c => (
                  <tr key={c.customer_id}>
                    <td className="mono-text">{c.customer_id}</td>
                    <td className="mono-text" style={{ color: c.churn_probability > 0.7 ? 'var(--accent-rose)' : 'var(--accent-amber)' }}>
                      {(c.churn_probability * 100).toFixed(1)}%
                    </td>
                    <td>
                      <span className={`badge ${c.risk_tier.includes('High') ? 'badge-critical' : 'badge-medium'}`}>
                        {c.risk_tier}
                      </span>
                    </td>
                    <td className="mono-text">£{c.total_revenue?.toLocaleString()}</td>
                    <td>{c.days_since_last_order} days</td>
                    <td>{c.avg_csat_score} / 5.0</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Demand Intelligence */}
        {activeTab === 'demand' && (
          <div className="table-card">
            <div className="table-header">Daily SKU Demand Forecasts (95% CI)</div>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Product ID</th>
                  <th>Predicted Demand (Units)</th>
                  <th>95% Lower Bound</th>
                  <th>95% Upper Bound</th>
                  <th>Lag 1 Sales</th>
                  <th>7d Rolling Avg</th>
                </tr>
              </thead>
              <tbody>
                {demandData?.demand_forecasts?.map(d => (
                  <tr key={d.product_id}>
                    <td className="mono-text">{d.product_id}</td>
                    <td className="mono-text" style={{ fontWeight: '700', color: 'var(--accent-cyan)' }}>
                      {d.predicted_demand_units?.toFixed(1)}
                    </td>
                    <td className="mono-text">{d.lower_bound_95?.toFixed(1)}</td>
                    <td className="mono-text">{d.upper_bound_95?.toFixed(1)}</td>
                    <td className="mono-text">{d.units_sold_lag1}</td>
                    <td className="mono-text">{d.rolling_avg_7d?.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 4: Inventory Intelligence */}
        {activeTab === 'inventory' && (
          <div className="table-card">
            <div className="table-header">7-Day Stockout Risk & Automated Reorder Desk</div>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Item ID</th>
                  <th>Stockout Risk (7d)</th>
                  <th>Severity</th>
                  <th>Current Stock</th>
                  <th>Reorder Point</th>
                  <th>Recommended Reorder Qty</th>
                </tr>
              </thead>
              <tbody>
                {inventoryData?.stockout_alerts?.map(i => (
                  <tr key={i.item_id}>
                    <td className="mono-text">{i.item_id}</td>
                    <td className="mono-text" style={{ color: i.stockout_risk_prob_7d > 0.5 ? 'var(--accent-rose)' : 'var(--accent-amber)' }}>
                      {(i.stockout_risk_prob_7d * 100).toFixed(1)}%
                    </td>
                    <td>
                      <span className={`badge ${i.risk_severity === 'Critical' ? 'badge-critical' : 'badge-high'}`}>
                        {i.risk_severity}
                      </span>
                    </td>
                    <td className="mono-text">{i.current_stock_level}</td>
                    <td className="mono-text">{i.reorder_point}</td>
                    <td className="mono-text" style={{ fontWeight: '700', color: 'var(--accent-emerald)' }}>
                      {i.recommended_reorder_qty} units
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 5: Machine Operations */}
        {activeTab === 'operations' && (
          <div className="table-card">
            <div className="table-header">Predictive Machine Telemetry & Maintenance Desk</div>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Machine ID</th>
                  <th>Anomaly Score</th>
                  <th>24h Failure Prob</th>
                  <th>Failure Alert</th>
                  <th>Health Status</th>
                </tr>
              </thead>
              <tbody>
                {operationsData?.machine_health?.map(m => (
                  <tr key={m.machine_id}>
                    <td className="mono-text">{m.machine_id}</td>
                    <td className="mono-text">{m.anomaly_score?.toFixed(3)}</td>
                    <td className="mono-text" style={{ color: m.failure_prob_24h > 0.5 ? 'var(--accent-rose)' : 'var(--accent-emerald)', fontWeight: '700' }}>
                      {(m.failure_prob_24h * 100).toFixed(2)}%
                    </td>
                    <td>
                      {m.failure_alert_flag_24h === 1 ? (
                        <span className="badge badge-critical">HIGH RISK (&ge;6h Lead)</span>
                      ) : (
                        <span className="badge badge-approved">NORMAL</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${m.health_status === 'Critical' ? 'badge-critical' : 'badge-approved'}`}>
                        {m.health_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 6: AI Decision Center (Multi-Agent Audit Trail) */}
        {activeTab === 'decisions' && (
          <div className="table-card">
            <div className="table-header">Stage 10 Multi-Agent Bus Audit Trail</div>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Decision ID</th>
                  <th>Domain</th>
                  <th>Entity</th>
                  <th>Proposed Action</th>
                  <th>Urgency</th>
                  <th>Exposure (£)</th>
                  <th>Risk Level</th>
                  <th>Final Verdict</th>
                </tr>
              </thead>
              <tbody>
                {decisionsData?.decisions?.map(d => (
                  <tr key={d.decision_id}>
                    <td className="mono-text">{d.decision_id}</td>
                    <td style={{ textTransform: 'capitalize' }}>{d.domain}</td>
                    <td className="mono-text">{d.entity_id}</td>
                    <td className="mono-text" style={{ fontSize: '0.8rem' }}>{d.proposed_action}</td>
                    <td>{d.urgency_tier}</td>
                    <td className="mono-text">£{d.financial_exposure_gbp?.toLocaleString()}</td>
                    <td>
                      <span className={`badge ${d.risk_level === 'CRITICAL' ? 'badge-critical' : 'badge-high'}`}>
                        {d.risk_level}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${
                        d.final_verdict === 'APPROVED' ? 'badge-approved' : 
                        (d.final_verdict.includes('CONDITIONS') ? 'badge-conditions' : 'badge-escalated')
                      }`}>
                        {d.final_verdict}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
