"""
data_science/agents/agent_bus.py
==================================
Stage 10 — AgentBus: Multi-Agent Orchestrator

Coordinates the full agent pipeline for one decision run:
  1. Run 4 domain agents concurrently (ThreadPoolExecutor)
  2. Pass all outputs to CriticAgent
  3. Build stockout alert index for cross-domain Demand challenge
  4. Pass outputs + challenges to RiskAgent
  5. Pass all three to DecisionManager → Decision objects

Per-agent exceptions are isolated so one failing agent does not abort the run.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from data_science.agents.schemas import AgentOutput, CriticChallenge, Decision, Domain
from data_science.agents.customer_agent   import CustomerAgent
from data_science.agents.inventory_agent  import InventoryAgent
from data_science.agents.operations_agent import OperationsAgent
from data_science.agents.demand_agent     import DemandAgent
from data_science.agents.critic_agent     import CriticAgent
from data_science.agents.risk_agent       import RiskAgent
from data_science.agents.decision_manager import DecisionManager

logger = logging.getLogger(__name__)


class AgentBus:
    """
    Lightweight multi-agent orchestrator.

    Instantiates all agents, runs domain agents concurrently, coordinates
    governance agents sequentially (Critic then Risk), and delegates final
    decision assembly + persistence to DecisionManager.
    """

    def __init__(self, db_engine=None, max_workers: int = 4):
        self.engine      = db_engine
        self.max_workers = max_workers
        self.run_id      = uuid.uuid4()

        # Domain agents
        self.customer_agent   = CustomerAgent(db_engine=db_engine)
        self.inventory_agent  = InventoryAgent(db_engine=db_engine)
        self.operations_agent = OperationsAgent(db_engine=db_engine)
        self.demand_agent     = DemandAgent(db_engine=db_engine)

        # Governance agents
        self.critic_agent     = CriticAgent()
        self.risk_agent       = RiskAgent()

        # Decision manager
        self.decision_manager = DecisionManager(db_engine=db_engine)

        logger.info("AgentBus initialized. run_id=%s", self.run_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[Decision]:
        """
        Execute the full multi-agent decision pipeline.

        Returns:
            List of Decision objects produced by the DecisionManager.
        """
        logger.info("=" * 60)
        logger.info("AgentBus.run() started — run_id=%s", self.run_id)
        logger.info("=" * 60)

        # Step 1: Load contexts + run domain agents concurrently
        all_outputs = self._run_domain_agents()
        logger.info("Domain agents produced %d total recommendations.", len(all_outputs))

        if not all_outputs:
            logger.warning("AgentBus: No domain agent outputs produced. Exiting early.")
            return []

        # Step 2: Build stockout alert index for cross-domain Demand challenge
        stockout_alerts = self._build_stockout_index(all_outputs)

        # Step 3: Critic passes
        challenges = self.critic_agent.challenge_all(
            outputs=all_outputs,
            stockout_alerts=stockout_alerts,
        )
        challenged_count = sum(1 for c in challenges.values() if c.challenge_raised)
        logger.info("CriticAgent challenged %d / %d recommendations.", challenged_count, len(all_outputs))

        # Step 4: Risk assessment
        assessments = self.risk_agent.assess_all(
            outputs=all_outputs,
            challenges=challenges,
        )
        logger.info("RiskAgent completed %d assessments.", len(assessments))

        # Step 5: DecisionManager — final verdict + DB persistence + JSON export
        decisions = self.decision_manager.produce_decisions(
            outputs=all_outputs,
            challenges=challenges,
            assessments=assessments,
            run_id=self.run_id,
        )
        logger.info("DecisionManager produced %d final decisions.", len(decisions))

        # Step 6: Summary log
        self._log_decision_summary(decisions)

        logger.info("AgentBus.run() complete — run_id=%s", self.run_id)
        return decisions

    # ------------------------------------------------------------------
    # Internal: concurrent domain agent execution
    # ------------------------------------------------------------------

    def _run_domain_agents(self) -> List[AgentOutput]:
        """
        Load contexts and run all 4 domain agents concurrently.
        Returns the combined list of AgentOutput objects.
        """
        # Define agent tasks: (agent_name, load_fn, analyze_fn)
        agent_tasks = [
            ("CustomerAgent",   self.customer_agent),
            ("InventoryAgent",  self.inventory_agent),
            ("OperationsAgent", self.operations_agent),
            ("DemandAgent",     self.demand_agent),
        ]

        all_outputs: List[AgentOutput] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for agent_name, agent in agent_tasks:
                future = executor.submit(self._run_single_domain_agent, agent_name, agent)
                futures[future] = agent_name

            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    outputs = future.result()
                    all_outputs.extend(outputs)
                    logger.info(
                        "%s completed: %d outputs.", agent_name, len(outputs)
                    )
                except Exception as exc:
                    logger.error(
                        "%s raised an exception and will be skipped: %s",
                        agent_name, exc, exc_info=True
                    )

        return all_outputs

    def _run_single_domain_agent(self, agent_name: str, agent) -> List[AgentOutput]:
        """Load contexts and run analyze_batch for one domain agent."""
        logger.info("Running %s...", agent_name)
        contexts = agent.load_contexts()
        if not contexts:
            logger.info("%s: no contexts loaded.", agent_name)
            return []
        outputs = agent.analyze_batch(contexts)
        return outputs

    # ------------------------------------------------------------------
    # Internal: cross-domain index
    # ------------------------------------------------------------------

    def _build_stockout_index(self, outputs: List[AgentOutput]) -> Dict[str, float]:
        """
        Build a dict of entity_id → stockout_risk_prob_7d from InventoryAgent outputs.
        Used by CriticAgent to detect Demand vs Inventory conflicts.
        """
        index: Dict[str, float] = {}
        for output in outputs:
            if output.domain == Domain.INVENTORY:
                stockout_prob = output.evidence.get("stockout_risk_prob_7d", 0.0)
                index[output.entity_id] = stockout_prob
        return index

    # ------------------------------------------------------------------
    # Internal: summary log
    # ------------------------------------------------------------------

    def _log_decision_summary(self, decisions: List[Decision]) -> None:
        """Print a formatted decision summary table to the log."""
        if not decisions:
            return

        logger.info("\n" + "=" * 80)
        logger.info("DECISION SUMMARY — run_id=%s", self.run_id)
        logger.info("=" * 80)
        header = f"{'Domain':<14} {'Entity':<20} {'Verdict':<28} {'Confidence':>10} {'HumanApproval':>14}"
        logger.info(header)
        logger.info("-" * 80)
        for d in decisions:
            row = (
                f"{d.domain.value:<14} "
                f"{d.entity_id:<20} "
                f"{d.final_verdict.value:<28} "
                f"{d.confidence_score:>10.1%} "
                f"{'YES' if d.requires_human_approval else 'no':>14}"
            )
            logger.info(row)
        logger.info("=" * 80)
