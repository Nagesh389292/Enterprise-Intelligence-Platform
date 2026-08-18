"""
data_science/agents/base.py
============================
Stage 10 — Abstract BaseAgent class.

All domain agents (CustomerAgent, InventoryAgent, OperationsAgent, DemandAgent)
extend BaseAgent and implement the `analyze()` method.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List

from data_science.agents.schemas import AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for all domain agents in the multi-agent decision system.

    Subclasses must implement:
        analyze(context: AgentContext) -> AgentOutput

    The AgentBus calls analyze() for each entity context.
    Agents do not communicate directly with each other —
    all inter-agent coordination is handled by the AgentBus,
    CriticAgent, RiskAgent, and DecisionManager.
    """

    agent_name: str = "BaseAgent"
    domain: str = "base"
    version: str = "1.0.0"

    def __init__(self):
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    @abstractmethod
    def analyze(self, context: AgentContext) -> AgentOutput:
        """
        Analyze the prediction payload in `context` and produce
        a structured AgentOutput recommendation.

        Args:
            context: AgentContext containing prediction data + business context

        Returns:
            AgentOutput with the recommended action, confidence, and reasoning
        """
        ...

    def analyze_batch(self, contexts: List[AgentContext]) -> List[AgentOutput]:
        """
        Analyze a list of entity contexts and return a list of outputs.
        Per-entity exceptions are caught and logged so one failure does
        not abort the entire batch.
        """
        results = []
        for ctx in contexts:
            try:
                output = self.analyze(ctx)
                results.append(output)
            except Exception as exc:
                self.logger.error(
                    "Agent %s failed on entity %s: %s",
                    self.agent_name, ctx.entity_id, exc, exc_info=True
                )
        return results

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} domain={self.domain} v{self.version}>"
