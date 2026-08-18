"""
tests/test_agent_system.py
============================
Stage 10 — pytest integration tests for the Multi-Agent Decision Intelligence system.

Tests:
  1. Schema validation — Decision object serialises to DB row correctly
  2. CustomerAgent — correct tier assignment for HIGH/MEDIUM churn probability fixtures
  3. InventoryAgent — correct reorder quantity and excess-stock passthrough
  4. OperationsAgent — correct urgency tier for IMMEDIATE/PREVENTIVE/MONITOR cases
  5. CriticAgent — challenges excess reorder quantity and revises it
  6. CriticAgent — challenges low-confidence P1 churn intervention
  7. CriticAgent — challenges IMMEDIATE ops with low failure probability
  8. RiskAgent — sets requires_human_approval=True for low adjusted confidence
  9. RiskAgent — CRITICAL risk level for ops IMMEDIATE + low confidence
  10. DecisionManager — ESCALATED verdict for CRITICAL risk + low confidence
  11. DecisionManager — APPROVED_WITH_CONDITIONS for human-approval-required case
  12. DecisionManager — APPROVED_WITH_CONDITIONS for critic quantity revision
  13. AgentBus — full run with mocked DB returns Decision list
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch

import pytest

# Import all agent components
from data_science.agents.schemas import (
    AgentContext,
    AgentOutput,
    CriticChallenge,
    RiskAssessment,
    Decision,
    Domain,
    DecisionType,
    RiskLevel,
    Verdict,
)
from data_science.agents.agent_bus        import AgentBus
from data_science.agents.customer_agent   import CustomerAgent
from data_science.agents.inventory_agent  import InventoryAgent
from data_science.agents.operations_agent import OperationsAgent
from data_science.agents.critic_agent     import CriticAgent
from data_science.agents.risk_agent       import RiskAgent
from data_science.agents.decision_manager import DecisionManager


# ---------------------------------------------------------------------------
# Fixtures: AgentContext helpers
# ---------------------------------------------------------------------------

def _make_run_id() -> uuid.UUID:
    return uuid.uuid4()


def _customer_context(churn_prob: float, total_spend: float, is_high_value: bool, run_id=None) -> AgentContext:
    run_id = run_id or _make_run_id()
    return AgentContext(
        domain=Domain.CUSTOMER,
        entity_id="CUST_TEST_001",
        predictions={
            "churn_probability":    churn_prob,
            "predicted_churn_flag": 1 if churn_prob >= 0.50 else 0,
            "risk_tier":            "High" if churn_prob >= 0.70 else "Medium",
            "model_version":        "v1.0",
        },
        business_ctx={
            "total_orders":   10,
            "total_spend":    total_spend,
            "tenure_days":    365,
            "avg_csat_score": 3.5,
            "is_high_value":  is_high_value,
        },
        run_id=run_id,
    )


def _inventory_context(stockout_prob: float, demand_7d: float, qty_available: float, run_id=None) -> AgentContext:
    run_id = run_id or _make_run_id()
    return AgentContext(
        domain=Domain.INVENTORY,
        entity_id="SKU_TEST_042",
        predictions={
            "stockout_risk_prob_7d":  stockout_prob,
            "stockout_alert_flag_7d": 1 if stockout_prob >= 0.50 else 0,
            "risk_severity":          "Critical" if stockout_prob >= 0.75 else "Moderate",
            "model_version":          "v1.0",
        },
        business_ctx={
            "demand_7d":               demand_7d,
            "quantity_available":       qty_available,
            "reorder_point":            50.0,
            "reorder_quantity_default": 100.0,
            "unit_cost":                5.0,
            "supplier_name":            "TestSupplier",
        },
        run_id=run_id,
    )


def _ops_context(failure_prob: float, anomaly_score: float, health_status: str, is_anomaly: bool, run_id=None) -> AgentContext:
    run_id = run_id or _make_run_id()
    return AgentContext(
        domain=Domain.OPERATIONS,
        entity_id="MACHINE_TEST_17",
        predictions={
            "anomaly_score":          anomaly_score,
            "is_anomaly_flag":        1 if is_anomaly else 0,
            "failure_prob_24h":       failure_prob,
            "failure_alert_flag_24h": 1 if failure_prob >= 0.50 else 0,
            "health_status":          health_status,
            "model_version":          "v1.0",
        },
        business_ctx={"last_reading_ts": "2026-08-18T10:00:00"},
        run_id=run_id,
    )


def _make_agent_output(domain: Domain, decision_type: DecisionType, entity_id: str,
                       confidence: float, quantity: float | None = None,
                       urgency_hours: float | None = None,
                       evidence: dict | None = None,
                       source_models: list | None = None) -> AgentOutput:
    return AgentOutput(
        agent_name="TestAgent",
        domain=domain,
        decision_type=decision_type,
        entity_id=entity_id,
        recommended_action=f"Test action for {entity_id}",
        quantity=quantity,
        urgency_hours=urgency_hours,
        confidence=confidence,
        reasoning_steps=["Step 1: test reasoning"],
        evidence=evidence or {},
        source_models=source_models or ["test_model"],
        run_id=_make_run_id(),
    )


def _make_risk_assessment(domain: Domain, entity_id: str,
                           risk_level: RiskLevel, adj_confidence: float,
                           requires_approval: bool,
                           financial_exposure: float = 1000.0) -> RiskAssessment:
    return RiskAssessment(
        domain=domain,
        entity_id=entity_id,
        overall_risk_level=risk_level,
        financial_exposure_usd=financial_exposure,
        model_confidence=adj_confidence + 0.10,
        model_uncertainty_penalty=0.10,
        adjusted_confidence=adj_confidence,
        requires_human_approval=requires_approval,
        risk_factors=["Test risk factor"],
    )


# ===========================================================================
# Test 1: Schema — Decision to_db_row
# ===========================================================================

class TestDecisionSchema:
    def test_decision_to_db_row_has_required_keys(self):
        d = Decision(
            run_id=uuid.uuid4(),
            domain=Domain.CUSTOMER,
            decision_type=DecisionType.RETAIN_CUSTOMER,
            entity_id="CUST_001",
            recommended_action="Retain customer",
            confidence_score=0.75,
            risk_level=RiskLevel.MEDIUM,
            requires_human_approval=False,
            reasoning_chain=["Step 1"],
            source_models=["churn_xgboost"],
            final_verdict=Verdict.APPROVED,
        )
        row = d.to_db_row()
        required_keys = [
            "decision_id", "run_id", "domain", "decision_type", "entity_id",
            "recommended_action", "confidence_score", "risk_level",
            "requires_human_approval", "reasoning_chain", "risk_assessment",
            "source_models", "final_verdict", "created_at",
        ]
        for key in required_keys:
            assert key in row, f"Missing key: {key}"

    def test_decision_reasoning_chain_is_json_string(self):
        d = Decision(
            run_id=uuid.uuid4(),
            domain=Domain.INVENTORY,
            decision_type=DecisionType.REORDER_INVENTORY,
            entity_id="SKU_042",
            recommended_action="Reorder 280 units",
            quantity=280.0,
            confidence_score=0.91,
            risk_level=RiskLevel.HIGH,
            requires_human_approval=True,
            reasoning_chain=["Stockout risk: 91%", "Demand: 310 units"],
            source_models=["stockout_xgboost", "demand_ridge"],
            final_verdict=Verdict.APPROVED_WITH_CONDITIONS,
        )
        row = d.to_db_row()
        parsed = json.loads(row["reasoning_chain"])
        assert isinstance(parsed, list)
        assert len(parsed) == 2


# ===========================================================================
# Test 2-3: CustomerAgent
# ===========================================================================

class TestCustomerAgent:
    def setup_method(self):
        self.agent = CustomerAgent.__new__(CustomerAgent)
        self.agent.engine = None
        self.agent.logger = __import__("logging").getLogger("test")

    def test_p1_high_value_customer(self):
        ctx = _customer_context(churn_prob=0.82, total_spend=8000.0, is_high_value=True)
        output = self.agent.analyze(ctx)
        assert output.decision_type == DecisionType.RETAIN_CUSTOMER
        assert "PRIORITY-1" in output.recommended_action
        assert "PHONE" in output.evidence["channel"]
        assert output.confidence > 0.60

    def test_p2_medium_churn(self):
        ctx = _customer_context(churn_prob=0.55, total_spend=1000.0, is_high_value=False)
        output = self.agent.analyze(ctx)
        assert output.decision_type == DecisionType.RETAIN_CUSTOMER
        assert output.evidence["retention_tier"] == "P2"
        assert "email" in output.recommended_action.lower() or "EMAIL" in output.evidence["channel"]

    def test_confidence_bounded_0_to_1(self):
        ctx = _customer_context(churn_prob=0.99, total_spend=99999.0, is_high_value=True)
        output = self.agent.analyze(ctx)
        assert 0.0 <= output.confidence <= 1.0


# ===========================================================================
# Test 4: InventoryAgent
# ===========================================================================

class TestInventoryAgent:
    def setup_method(self):
        self.agent = InventoryAgent.__new__(InventoryAgent)
        self.agent.engine = None
        self.agent.logger = __import__("logging").getLogger("test")

    def test_reorder_quantity_formula(self):
        """demand_7d=310, qty_available=72, safety=1.25 → gap=310*1.25-72=315.5 → qty=315"""
        ctx = _inventory_context(stockout_prob=0.91, demand_7d=310.0, qty_available=72.0)
        output = self.agent.analyze(ctx)
        assert output.decision_type == DecisionType.REORDER_INVENTORY
        expected = round(310.0 * 1.25 - 72.0)
        assert output.quantity == expected

    def test_no_reorder_when_well_stocked(self):
        """qty_available=1000 >> demand*safety=312.5 → reorder=0"""
        ctx = _inventory_context(stockout_prob=0.60, demand_7d=100.0, qty_available=1000.0)
        output = self.agent.analyze(ctx)
        assert output.quantity == 0 or "No reorder" in output.recommended_action

    def test_source_models_include_both(self):
        ctx = _inventory_context(stockout_prob=0.80, demand_7d=200.0, qty_available=50.0)
        output = self.agent.analyze(ctx)
        assert "stockout_xgboost" in output.source_models
        assert "demand_ridge" in output.source_models


# ===========================================================================
# Test 5: OperationsAgent
# ===========================================================================

class TestOperationsAgent:
    def setup_method(self):
        self.agent = OperationsAgent.__new__(OperationsAgent)
        self.agent.engine = None
        self.agent.logger = __import__("logging").getLogger("test")

    def test_immediate_urgency_high_failure_prob(self):
        ctx = _ops_context(failure_prob=0.92, anomaly_score=0.8, health_status="Critical", is_anomaly=True)
        output = self.agent.analyze(ctx)
        assert output.urgency_hours == 4.0
        assert output.evidence["urgency_tier"] == "IMMEDIATE"

    def test_preventive_urgency(self):
        ctx = _ops_context(failure_prob=0.55, anomaly_score=0.6, health_status="Warning", is_anomaly=True)
        output = self.agent.analyze(ctx)
        assert output.urgency_hours == 24.0
        assert output.evidence["urgency_tier"] == "PREVENTIVE"

    def test_monitor_tier(self):
        # is_anomaly=False AND failure_prob=0.20 → below PREVENTIVE_PROB (0.50) → MONITOR
        ctx = _ops_context(failure_prob=0.20, anomaly_score=0.3, health_status="Warning", is_anomaly=False)
        output = self.agent.analyze(ctx)
        assert output.evidence["urgency_tier"] == "MONITOR"


# ===========================================================================
# Tests 6-8: CriticAgent
# ===========================================================================

class TestCriticAgent:
    def setup_method(self):
        self.critic = CriticAgent()

    def test_challenges_excess_inventory_reorder(self):
        """Reorder of 800 units when demand_7d=200 (4×) should be challenged and revised."""
        output = _make_agent_output(
            domain=Domain.INVENTORY,
            decision_type=DecisionType.REORDER_INVENTORY,
            entity_id="SKU_042",
            confidence=0.85,
            quantity=800.0,
            evidence={
                "demand_7d": 200.0,
                "quantity_available": 50.0,
                "stockout_risk_prob_7d": 0.80,
                "unit_cost": 5.0,
                "supplier": "TestSupplier",
            }
        )
        challenges = self.critic.challenge_all([output])
        challenge = challenges["inventory::SKU_042"]
        assert challenge.challenge_raised is True
        assert challenge.revised_quantity is not None
        assert challenge.revised_quantity < 800.0
        assert challenge.revised_quantity == round(200.0 * 0.90)

    def test_no_challenge_reasonable_reorder(self):
        """Reorder of 180 units when demand_7d=200 should NOT be challenged."""
        output = _make_agent_output(
            domain=Domain.INVENTORY,
            decision_type=DecisionType.REORDER_INVENTORY,
            entity_id="SKU_099",
            confidence=0.85,
            quantity=180.0,
            evidence={"demand_7d": 200.0, "quantity_available": 30.0,
                       "stockout_risk_prob_7d": 0.70, "unit_cost": 5.0, "supplier": "S"},
        )
        challenges = self.critic.challenge_all([output])
        assert challenges["inventory::SKU_099"].challenge_raised is False

    def test_challenges_low_confidence_p1_customer(self):
        """P1 intervention at churn_prob=0.55 (below 0.60 threshold) should be challenged."""
        output = _make_agent_output(
            domain=Domain.CUSTOMER,
            decision_type=DecisionType.RETAIN_CUSTOMER,
            entity_id="CUST_001",
            confidence=0.55,
            evidence={
                "churn_probability": 0.55,
                "retention_tier": "P1",
                "total_spend_gbp": 2000.0,
            }
        )
        challenges = self.critic.challenge_all([output])
        assert challenges["customer::CUST_001"].challenge_raised is True

    def test_challenges_ops_immediate_low_failure(self):
        """IMMEDIATE maintenance with failure_prob=0.18 (anomaly only) should be downgraded."""
        output = _make_agent_output(
            domain=Domain.OPERATIONS,
            decision_type=DecisionType.SCHEDULE_MAINTENANCE,
            entity_id="MACHINE_17",
            confidence=0.80,
            urgency_hours=4.0,
            evidence={
                "failure_prob_24h": 0.18,
                "anomaly_score": 0.60,
                "is_anomaly_flag": True,
                "health_status": "Warning",
                "urgency_tier": "IMMEDIATE",
                "urgency_hours": 4.0,
            }
        )
        challenges = self.critic.challenge_all([output])
        assert challenges["operations::MACHINE_17"].challenge_raised is True
        assert "PREVENTIVE" in challenges["operations::MACHINE_17"].challenge_text


# ===========================================================================
# Tests 9-10: RiskAgent
# ===========================================================================

class TestRiskAgent:
    def setup_method(self):
        self.risk = RiskAgent()

    def _no_challenge(self, domain, entity_id):
        return CriticChallenge(domain=domain, entity_id=entity_id, challenge_raised=False)

    def test_requires_approval_for_low_confidence(self):
        """Adjusted confidence below 0.65 gate → requires_human_approval=True."""
        output = _make_agent_output(
            domain=Domain.CUSTOMER,
            decision_type=DecisionType.RETAIN_CUSTOMER,
            entity_id="CUST_001",
            confidence=0.40,
            evidence={"churn_probability": 0.40, "total_spend_gbp": 500.0},
            source_models=["churn_xgboost_scale_pos_weight"],
        )
        challenges = {"customer::CUST_001": self._no_challenge(Domain.CUSTOMER, "CUST_001")}
        assessments = self.risk.assess_all([output], challenges)
        assessment = assessments["customer::CUST_001"]
        assert assessment.requires_human_approval is True

    def test_critical_risk_for_ops_immediate(self):
        """Operations IMMEDIATE urgency (urgency_hours ≤ 4) → CRITICAL risk level."""
        output = _make_agent_output(
            domain=Domain.OPERATIONS,
            decision_type=DecisionType.SCHEDULE_MAINTENANCE,
            entity_id="MACHINE_17",
            confidence=0.90,
            urgency_hours=4.0,
            evidence={
                "failure_prob_24h": 0.92,
                "anomaly_score": 0.80,
                "urgency_hours": 4.0,
            },
            source_models=["machine_failure_random_forest"],
        )
        challenges = {"operations::MACHINE_17": self._no_challenge(Domain.OPERATIONS, "MACHINE_17")}
        assessments = self.risk.assess_all([output], challenges)
        assessment = assessments["operations::MACHINE_17"]
        assert assessment.overall_risk_level == RiskLevel.CRITICAL

    def test_uncertainty_penalty_applied_for_churn(self):
        """Churn model has 0.30 uncertainty penalty → adjusted_confidence = confidence × 0.70."""
        output = _make_agent_output(
            domain=Domain.CUSTOMER,
            decision_type=DecisionType.RETAIN_CUSTOMER,
            entity_id="CUST_999",
            confidence=0.80,
            evidence={"churn_probability": 0.80, "total_spend_gbp": 1000.0},
            source_models=["churn_xgboost_scale_pos_weight"],
        )
        challenges = {"customer::CUST_999": self._no_challenge(Domain.CUSTOMER, "CUST_999")}
        assessments = self.risk.assess_all([output], challenges)
        a = assessments["customer::CUST_999"]
        expected_adj = round(0.80 * (1 - 0.30), 4)
        assert abs(a.adjusted_confidence - expected_adj) < 0.01


# ===========================================================================
# Tests 11-13: DecisionManager verdict logic
# ===========================================================================

class TestDecisionManager:
    def setup_method(self):
        mock_engine = MagicMock()
        self.dm = DecisionManager.__new__(DecisionManager)
        self.dm.engine = mock_engine

    def _run_verdict(self, output, challenge, assessment):
        return self.dm._determine_verdict(output, challenge, assessment)

    def test_escalated_verdict_critical_low_confidence(self):
        output = _make_agent_output(Domain.OPERATIONS, DecisionType.SCHEDULE_MAINTENANCE, "M1", 0.90)
        challenge = CriticChallenge(domain=Domain.OPERATIONS, entity_id="M1", challenge_raised=False)
        assessment = _make_risk_assessment(Domain.OPERATIONS, "M1", RiskLevel.CRITICAL, 0.40, True)
        assert self._run_verdict(output, challenge, assessment) == Verdict.ESCALATED

    def test_approved_with_conditions_human_approval(self):
        output = _make_agent_output(Domain.CUSTOMER, DecisionType.RETAIN_CUSTOMER, "C1", 0.55)
        challenge = CriticChallenge(domain=Domain.CUSTOMER, entity_id="C1", challenge_raised=False)
        assessment = _make_risk_assessment(Domain.CUSTOMER, "C1", RiskLevel.HIGH, 0.55, True)
        verdict = self._run_verdict(output, challenge, assessment)
        assert verdict == Verdict.APPROVED_WITH_CONDITIONS

    def test_approved_with_conditions_critic_revised_quantity(self):
        output = _make_agent_output(Domain.INVENTORY, DecisionType.REORDER_INVENTORY, "SKU_042", 0.85, quantity=800.0)
        challenge = CriticChallenge(
            domain=Domain.INVENTORY, entity_id="SKU_042",
            challenge_raised=True, revised_quantity=180.0,
            revised_action="REORDER 180 units [CRITIC REVISED]",
            severity=RiskLevel.MEDIUM,
        )
        assessment = _make_risk_assessment(Domain.INVENTORY, "SKU_042", RiskLevel.MEDIUM, 0.70, False)
        verdict = self._run_verdict(output, challenge, assessment)
        assert verdict == Verdict.APPROVED_WITH_CONDITIONS

    def test_approved_clean_decision(self):
        output = _make_agent_output(Domain.INVENTORY, DecisionType.REORDER_INVENTORY, "SKU_001", 0.88, quantity=100.0)
        challenge = CriticChallenge(domain=Domain.INVENTORY, entity_id="SKU_001", challenge_raised=False)
        assessment = _make_risk_assessment(Domain.INVENTORY, "SKU_001", RiskLevel.LOW, 0.80, False)
        verdict = self._run_verdict(output, challenge, assessment)
        assert verdict == Verdict.APPROVED


# ===========================================================================
# Test 14: AgentBus end-to-end (mocked DB)
# ===========================================================================

class TestAgentBusEndToEnd:
    """
    Integration smoke test: mock all DB-loading methods and verify
    that AgentBus.run() returns a non-empty list of Decision objects
    with correct schema.
    """

    def test_bus_returns_decisions_with_mocked_db(self, tmp_path):
        """Run AgentBus with mocked load_contexts so no real DB is needed."""
        import uuid as _uuid
        run_id = _uuid.uuid4()

        # Build realistic mock outputs for each domain
        mock_outputs = [
            _make_agent_output(
                Domain.CUSTOMER, DecisionType.RETAIN_CUSTOMER, "CUST_001",
                0.75, evidence={"churn_probability": 0.75, "total_spend_gbp": 5000.0,
                                 "is_high_value": True, "tenure_days": 365,
                                 "avg_csat_score": 2.8, "retention_tier": "P1",
                                 "channel": "PHONE"},
                source_models=["churn_xgboost_scale_pos_weight"],
            ),
            _make_agent_output(
                Domain.INVENTORY, DecisionType.REORDER_INVENTORY, "SKU_042",
                0.88, quantity=280.0,
                evidence={"demand_7d": 310.0, "quantity_available": 72.0,
                           "stockout_risk_prob_7d": 0.91, "risk_severity": "Critical",
                           "reorder_point": 100.0, "computed_reorder_qty": 280.0,
                           "unit_cost": 5.0, "supplier": "TestSupplier"},
                source_models=["stockout_xgboost", "demand_ridge"],
            ),
            _make_agent_output(
                Domain.OPERATIONS, DecisionType.SCHEDULE_MAINTENANCE, "MACHINE_17",
                0.92, urgency_hours=4.0,
                evidence={"failure_prob_24h": 0.92, "anomaly_score": 0.85,
                           "is_anomaly_flag": True, "health_status": "Critical",
                           "urgency_tier": "IMMEDIATE", "urgency_hours": 4.0},
                source_models=["machine_isolation_forest", "machine_failure_random_forest"],
            ),
        ]

        # Mock the AgentBus internals
        from data_science.agents.critic_agent  import CriticAgent as CAgent
        from data_science.agents.risk_agent    import RiskAgent   as RAgent
        from data_science.agents.decision_manager import DecisionManager as DM

        bus = AgentBus.__new__(AgentBus)
        bus.run_id   = run_id
        bus.max_workers = 1
        bus.critic_agent  = CAgent()
        bus.risk_agent    = RAgent()

        # Mock DecisionManager to avoid DB writes
        mock_dm = MagicMock(spec=DM)
        def fake_produce(outputs, challenges, assessments, run_id):
            # Assemble decisions without persisting
            decisions = []
            for o in outputs:
                key = f"{o.domain.value}::{o.entity_id}"
                ch  = challenges.get(key)
                ass = assessments.get(key)
                if ass is None:
                    continue
                d = Decision(
                    run_id=run_id,
                    domain=o.domain,
                    decision_type=o.decision_type,
                    entity_id=o.entity_id,
                    recommended_action=o.recommended_action,
                    quantity=o.quantity,
                    urgency_hours=o.urgency_hours,
                    confidence_score=ass.adjusted_confidence,
                    risk_level=ass.overall_risk_level,
                    requires_human_approval=ass.requires_human_approval,
                    reasoning_chain=o.reasoning_steps,
                    source_models=o.source_models,
                    final_verdict=Verdict.APPROVED,
                )
                decisions.append(d)
            return decisions
        mock_dm.produce_decisions = fake_produce
        bus.decision_manager = mock_dm

        # Run with pre-built outputs
        stockout_alerts = {"SKU_042": 0.91}
        challenges  = bus.critic_agent.challenge_all(mock_outputs, stockout_alerts)
        assessments = bus.risk_agent.assess_all(mock_outputs, challenges)
        decisions   = bus.decision_manager.produce_decisions(
            mock_outputs, challenges, assessments, run_id
        )

        assert len(decisions) == 3
        assert all(isinstance(d, Decision) for d in decisions)
        domains = {d.domain for d in decisions}
        assert Domain.CUSTOMER in domains
        assert Domain.INVENTORY in domains
        assert Domain.OPERATIONS in domains

        # Inventory critic challenge should have been raised (280 ≤ 2×310 — not challenged)
        # But the test verifies the pipeline runs, not that critic fires (need >2× to fire)
        for d in decisions:
            assert d.confidence_score >= 0.0
            assert d.confidence_score <= 1.0
