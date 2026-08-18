-- =============================================================================
-- Enterprise Intelligence Platform - Stage 10 Multi-Agent Decision Audit Log
-- Schema: analytics
-- Table:  analytics.agent_decisions
-- =============================================================================
-- Persists every structured Decision emitted by the DecisionManager.
-- One row per entity-level recommendation, including full reasoning chain,
-- critic challenge, risk assessment, and final verdict.
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.agent_decisions (
    -- Identity
    decision_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID NOT NULL,                          -- groups all decisions in one AgentBus run

    -- Domain & Entity
    domain              VARCHAR(30)  NOT NULL,                 -- customer | inventory | operations | demand
    decision_type       VARCHAR(50)  NOT NULL,                 -- RETAIN_CUSTOMER | REORDER_INVENTORY | SCHEDULE_MAINTENANCE | ADJUST_DEMAND_PLAN
    entity_id           VARCHAR(100) NOT NULL,                 -- customer_id | product_id | machine_id

    -- Recommendation
    recommended_action  TEXT         NOT NULL,
    quantity            DOUBLE PRECISION,                      -- units to reorder (inventory) or null
    urgency_hours       DOUBLE PRECISION,                      -- hours until maintenance needed (ops) or null

    -- Confidence & Risk
    confidence_score    DOUBLE PRECISION NOT NULL,             -- 0.0 – 1.0
    risk_level          VARCHAR(20)  NOT NULL,                 -- LOW | MEDIUM | HIGH | CRITICAL
    requires_human_approval BOOLEAN  NOT NULL DEFAULT FALSE,

    -- Agent Reasoning (structured JSONB for queryability)
    reasoning_chain     JSONB        NOT NULL DEFAULT '[]',    -- ordered list of reasoning step strings
    critic_challenge    TEXT,                                  -- what the CriticAgent challenged (null if no challenge)
    risk_assessment     JSONB        NOT NULL DEFAULT '{}',    -- RiskAgent output: exposure, uncertainty, factors

    -- Provenance
    source_models       TEXT[]       NOT NULL DEFAULT '{}',   -- e.g. ['stockout_xgboost','demand_ridge']
    final_verdict       VARCHAR(30)  NOT NULL,                 -- APPROVED | APPROVED_WITH_CONDITIONS | REJECTED | ESCALATED

    -- Timestamps
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_agent_decisions_run_id
    ON analytics.agent_decisions(run_id);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_domain_verdict
    ON analytics.agent_decisions(domain, final_verdict);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_entity
    ON analytics.agent_decisions(entity_id);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_risk_approval
    ON analytics.agent_decisions(risk_level, requires_human_approval);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_created_at
    ON analytics.agent_decisions(created_at DESC);

-- Comments
COMMENT ON TABLE analytics.agent_decisions IS
    'Stage 10: Structured audit log for all multi-agent AI decisions. '
    'One row per entity recommendation produced by the AgentBus orchestrator. '
    'Queryable by domain, verdict, risk level, and human approval status.';

COMMENT ON COLUMN analytics.agent_decisions.reasoning_chain IS
    'JSON array of strings: ordered human-readable reasoning steps applied by the domain agent.';

COMMENT ON COLUMN analytics.agent_decisions.critic_challenge IS
    'Textual description of CriticAgent challenge to the domain recommendation. NULL if no challenge raised.';

COMMENT ON COLUMN analytics.agent_decisions.risk_assessment IS
    'JSON object from RiskAgent: financial_exposure_usd, model_uncertainty_penalty, risk_factors list.';

COMMENT ON COLUMN analytics.agent_decisions.source_models IS
    'Array of model artifact names that contributed predictions to this decision.';
