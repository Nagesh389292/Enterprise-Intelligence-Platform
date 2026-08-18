# Stage 10 — Multi-Agent Decision Intelligence: Architecture Guide

## Overview

Stage 10 implements a **deterministic, rule-governed multi-agent decisioning layer** that sits directly on top of the Stage 9 prediction store. It converts 119,500 structured ML predictions into auditable, human-reviewable business decisions without relying on any LLM.

---

## Agent Topology

```
PostgreSQL / dbt Gold + analytics.fact_predictions_*
                    │
        ┌───────────┼───────────┬──────────────┐
        ▼           ▼           ▼              ▼
  CustomerAgent  InventoryAgent  OperationsAgent  DemandAgent
  (churn →        (stockout +     (telemetry →     (demand forecast
   retention)      demand →        maintenance)      → purchase plan)
                   reorder)
        │           │           │              │
        └───────────┴───────────┴──────────────┘
                         │  (list[AgentOutput])
                         ▼
                    CriticAgent
                  (challenges 4 rules)
                         │  (dict[entity → CriticChallenge])
                         ▼
                    RiskAgent
                  (financial + uncertainty scoring)
                         │  (dict[entity → RiskAssessment])
                         ▼
                   DecisionManager
                  (verdict logic → Decision objects)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
  analytics.agent_decisions    docs/agents/
  (PostgreSQL audit log)       decision_audit_YYYYMMDD.json
```

---

## Agent Contracts

### Domain Agents

All domain agents inherit `BaseAgent` and implement `analyze(context: AgentContext) → AgentOutput`.

| Agent | Input Table | Output | Key Evidence |
|---|---|---|---|
| `CustomerAgent` | `fact_predictions_customer_churn` | `RETAIN_CUSTOMER` | `churn_probability`, `total_spend`, `risk_tier` |
| `InventoryAgent` | `fact_predictions_inventory_stockout` + `fact_predictions_sku_demand` | `REORDER_INVENTORY` | `stockout_risk_prob_7d`, `demand_7d`, `quantity_available` |
| `OperationsAgent` | `fact_predictions_machine_health` | `SCHEDULE_MAINTENANCE` | `failure_prob_24h`, `anomaly_score`, `health_status` |
| `DemandAgent` | `fact_predictions_sku_demand` | `ADJUST_DEMAND_PLAN` | `demand_7d`, `quantity_available`, `days_of_supply` |

### Governance Agents

| Agent | Input | Output | Challenge Rules |
|---|---|---|---|
| `CriticAgent` | `list[AgentOutput]` | `dict[str, CriticChallenge]` | 4 quantitative rules (see below) |
| `RiskAgent` | `list[AgentOutput]` + challenges | `dict[str, RiskAssessment]` | financial exposure + model uncertainty |

### DecisionManager

| Input | Output |
|---|---|
| `(AgentOutput, CriticChallenge, RiskAssessment)` per entity | `Decision` (persisted to PostgreSQL + JSON log) |

---

## Critic Challenge Rules

### Rule 1 — Inventory Excess Reorder

**Trigger:** `reorder_qty > 2 × demand_7d`

**Challenge:**
```
"Proposed reorder of 500 units exceeds 2× the 7-day demand forecast
(200 units). Current inventory covers 72 units. Ordering 500 creates
300 units excess exposure. Recommend revising to 180 units
(= demand_7d × 0.90)."
```

**Revised quantity:** `round(demand_7d × 0.90)`

---

### Rule 2 — Low-Confidence P1 Churn Intervention

**Trigger:** `retention_tier = "P1"` AND `churn_probability < 0.60`

**Challenge:**
```
"Churn probability 55% is below the high-confidence threshold (60%)
for P1 intervention. ROI on phone + discount at this confidence level
is uncertain. Recommend downgrading to P2 (email-only) intervention."
```

---

### Rule 3 — Operations Urgency Overclassification

**Trigger:** `is_anomaly = True` AND `failure_prob_24h < 0.30` AND `urgency_tier = IMMEDIATE`

**Challenge:**
```
"Anomaly flag is set but 24h failure probability is only 18%
(below 30%). IMMEDIATE dispatch is disproportionate.
Recommend downgrading to PREVENTIVE maintenance (24-hour window)."
```

---

### Rule 4 — Demand vs Inventory Conflict

**Trigger:** `direction = INCREASE_STOCK_ORDER` AND stockout entity already flagged CRITICAL

**Challenge:**
```
"DemandAgent recommends INCREASE_STOCK_ORDER for SKU-042,
but Inventory stockout risk is already CRITICAL (91%).
Confirm InventoryAgent has already generated a reorder recommendation
to avoid duplicate orders."
```

---

## Risk Scoring Methodology

### Model Uncertainty Penalties

Derived directly from Stage 8 audit results:

| Model | Source Audit | PR-AUC / WAPE | Penalty |
|---|---|---|---|
| `churn_xgboost_scale_pos_weight` | Stage 8A | PR-AUC = 0.057 | **30%** |
| `demand_ridge` | Stage 8B | WAPE = 61% | **15%** |
| `machine_isolation_forest` | Stage 8D | Unsupervised | **10%** |
| `machine_failure_random_forest` | Stage 8D | 100% event recall | **5%** |
| `stockout_xgboost` | Stage 8C | PR-AUC = 0.9425 | **5%** |

### Adjusted Confidence

```
adjusted_confidence = model_confidence × (1 - uncertainty_penalty)
```

### Human Approval Gate

A decision `requires_human_approval = True` if any of:
- `adjusted_confidence < 0.65`
- `financial_exposure_usd ≥ £50,000`
- `overall_risk_level = CRITICAL`

---

## Verdict Logic

| Condition | Verdict |
|---|---|
| `risk_level = CRITICAL` AND `adjusted_confidence < 0.50` | `ESCALATED` |
| Critic raised challenge AND no revised_action AND severity ≥ HIGH | `REJECTED` |
| `requires_human_approval = True` OR critic revised quantity | `APPROVED_WITH_CONDITIONS` |
| All other passing cases | `APPROVED` |

---

## Decision Audit Log Schema

The JSON audit log (`docs/agents/decision_audit_YYYYMMDD.json`) has the following top-level structure:

```json
{
  "run_id": "uuid",
  "generated_at": "ISO-8601",
  "total_decisions": 42,
  "summary": {
    "by_domain":  {"customer": 5, "inventory": 12, ...},
    "by_verdict": {"APPROVED": 8, "APPROVED_WITH_CONDITIONS": 20, ...},
    "by_risk":    {"LOW": 3, "MEDIUM": 15, ...},
    "requiring_human_approval": 14
  },
  "decisions": [
    {
      "decision_id":             "uuid",
      "domain":                  "inventory",
      "decision_type":           "REORDER_INVENTORY",
      "entity_id":               "SKU-1042",
      "recommended_action":      "REORDER 280 units of SKU-1042 from Supplier-A [CRITIC REVISED from 500].",
      "quantity":                280,
      "urgency_hours":           null,
      "confidence_score":        0.7735,
      "risk_level":              "HIGH",
      "requires_human_approval": true,
      "final_verdict":           "APPROVED_WITH_CONDITIONS",
      "source_models":           ["stockout_xgboost", "demand_ridge"],
      "critic_challenge":        "Proposed reorder of 500 units exceeds 2× demand forecast...",
      "reasoning_chain": [
        "Stockout risk: 91% over 7 days (severity=Critical)",
        "Current inventory: 72 units | Reorder point: 100 units",
        "7-day demand forecast: 310.0 units (Ridge regression champion)",
        "Reorder formula: max(0, 310.0×1.25 - 72) = 315.5 → rounded to 316",
        "Reorder 316 units from 'Supplier-A' (est. cost: £1,580)",
        "[CriticAgent] Proposed reorder of 316 exceeds 2×demand...",
        "[RiskAgent] High model uncertainty penalty (15%) — Ridge WAPE=61%."
      ],
      "risk_assessment": {
        "financial_exposure_usd": 1400.0,
        "model_confidence": 0.91,
        "model_uncertainty_penalty": 0.10,
        "adjusted_confidence": 0.7735,
        "requires_human_approval": true,
        "risk_factors": [...]
      }
    }
  ]
}
```

---

## Adding a New Domain Agent

1. Create `data_science/agents/my_new_agent.py`
2. Inherit `BaseAgent`, set `agent_name`, `domain`, `version`
3. Implement `load_contexts() → List[AgentContext]` and `analyze(context) → AgentOutput`
4. Register in `AgentBus.__init__()` and `_run_domain_agents()`
5. Add CriticAgent challenge rule in `critic_agent.py::_challenge_single()`
6. Add unit tests in `tests/test_agent_system.py`

---

## Running Stage 10

```bash
# Apply DDL + run full agent pipeline
.\\venv\\Scripts\\python.exe scripts\\run_stage10_agents.py

# Run unit tests only
.\\venv\\Scripts\\python.exe -m pytest tests/test_agent_system.py -v
```

---

## Key Design Decisions

**Why no LLM?**
All reasoning is deterministic Python operating on structured prediction payloads. Every decision is reproducible and unit-testable. The Critic's "500 units is excessive" challenge is derived from `demand_7d` — not hallucinated.

**Why `ThreadPoolExecutor` in AgentBus?**
The 4 domain agents are independent DB reads. Concurrent execution reduces latency ~4×.

**Why the 30% uncertainty penalty for churn?**
Stage 8A achieved PR-AUC = 0.057. The system is honest about this weakness by applying a proportional penalty to adjusted_confidence for all churn-driven decisions, rather than pretending the model has 90% accuracy.

**Why is `analytics.agent_decisions` JSONB for reasoning_chain?**
The reasoning chain length varies by entity complexity. JSONB stores it efficiently while remaining fully queryable via PostgreSQL JSON operators.
