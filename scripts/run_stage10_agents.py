"""
scripts/run_stage10_agents.py
==============================
Stage 10 — Master CLI runner for the Multi-Agent Decision Intelligence system.

Execution sequence:
  1. Apply DDL (create analytics.agent_decisions if not exists)
  2. Verify DB connectivity + prediction table row counts
  3. Run AgentBus.run() — concurrent domain agents → Critic → Risk → DecisionManager
  4. Print decision summary table to stdout
  5. Save execution report to docs/agents/stage10_execution_report.md

Usage:
    .\\venv\\Scripts\\python.exe scripts/run_stage10_agents.py
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_science.db import get_engine
from data_science.agents.agent_bus import AgentBus
from data_science.agents.schemas import Verdict, RiskLevel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stage10_runner")

# ---------------------------------------------------------------------------
# Report path
# ---------------------------------------------------------------------------
DOCS_DIR    = PROJECT_ROOT / "docs" / "agents"
DDL_PATH    = PROJECT_ROOT / "sql" / "schema" / "10_agent_decisions.sql"
REPORT_PATH = DOCS_DIR / "stage10_execution_report.md"


# ---------------------------------------------------------------------------
# Step 1: Apply DDL
# ---------------------------------------------------------------------------

def apply_ddl(engine) -> None:
    """Create analytics.agent_decisions table if not exists."""
    logger.info("Applying DDL: %s", DDL_PATH)
    if not DDL_PATH.exists():
        logger.error("DDL file not found at %s", DDL_PATH)
        raise FileNotFoundError(f"Missing DDL: {DDL_PATH}")

    ddl_sql = DDL_PATH.read_text(encoding="utf-8")
    # Execute statement-by-statement (skip empty/comment-only blocks)
    statements = [s.strip() for s in ddl_sql.split(";") if s.strip() and not s.strip().startswith("--")]

    from sqlalchemy import text
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                # Non-fatal — table/index may already exist
                logger.debug("DDL stmt skipped (may already exist): %s", exc)

    logger.info("DDL applied successfully.")


# ---------------------------------------------------------------------------
# Step 2: Verify prediction table counts
# ---------------------------------------------------------------------------

def verify_prediction_store(engine) -> dict:
    """Query row counts from all 4 Stage 9 prediction tables."""
    from sqlalchemy import text

    tables = {
        "analytics.fact_predictions_customer_churn":    "Customer Churn",
        "analytics.fact_predictions_sku_demand":        "SKU Demand",
        "analytics.fact_predictions_inventory_stockout":"Inventory Stockout",
        "analytics.fact_predictions_machine_health":    "Machine Health",
    }

    counts = {}
    with engine.connect() as conn:
        for table, label in tables.items():
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                counts[label] = count
                logger.info("  %-30s %8d rows", label, count)
            except Exception as exc:
                counts[label] = 0
                logger.warning("  Could not query %s: %s", table, exc)

    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_ts = datetime.now(timezone.utc)
    logger.info("=" * 70)
    logger.info("STAGE 10 — ENTERPRISE MULTI-AGENT DECISION INTELLIGENCE")
    logger.info("Started: %s", start_ts.strftime("%Y-%m-%d %H:%M:%S UTC"))
    logger.info("=" * 70)

    engine = get_engine()

    # Step 1: DDL
    logger.info("\n[1/4] Applying DDL...")
    apply_ddl(engine)

    # Step 2: Verify prediction store
    logger.info("\n[2/4] Verifying prediction store...")
    pred_counts = verify_prediction_store(engine)
    total_preds = sum(pred_counts.values())
    logger.info("Total predictions available: %d", total_preds)

    if total_preds == 0:
        logger.error("Prediction store is empty. Run Stage 9 batch inference first.")
        sys.exit(1)

    # Step 3: Run AgentBus
    logger.info("\n[3/4] Running AgentBus...")
    bus = AgentBus(db_engine=engine, max_workers=4)
    decisions = bus.run()

    # Step 4: Summary
    logger.info("\n[4/4] Decision Summary")
    end_ts      = datetime.now(timezone.utc)
    elapsed_sec = (end_ts - start_ts).total_seconds()

    if not decisions:
        logger.warning("No decisions produced. Check prediction table data.")
        sys.exit(0)

    # Console table
    print("\n" + "=" * 110)
    print(f"  STAGE 10 DECISION SUMMARY  |  run_id={bus.run_id}  |  {len(decisions)} decisions")
    print("=" * 110)
    print(f"  {'Domain':<14} {'Entity':<22} {'Action':<40} {'Conf':>6} {'Risk':<10} {'Verdict':<28} {'HumanApproval'}")
    print("-" * 110)
    for d in decisions:
        action_short = d.recommended_action[:37] + "..." if len(d.recommended_action) > 40 else d.recommended_action
        print(
            f"  {d.domain.value:<14} "
            f"{d.entity_id:<22} "
            f"{action_short:<40} "
            f"{d.confidence_score:>5.1%} "
            f"{d.risk_level.value:<10} "
            f"{d.final_verdict.value:<28} "
            f"{'[YES]' if d.requires_human_approval else 'auto '}"
        )
    print("=" * 110)

    # Aggregate counts
    verdict_counts = {}
    for d in decisions:
        verdict_counts[d.final_verdict.value] = verdict_counts.get(d.final_verdict.value, 0) + 1
    domain_counts = {}
    for d in decisions:
        domain_counts[d.domain.value] = domain_counts.get(d.domain.value, 0) + 1
    approval_count = sum(1 for d in decisions if d.requires_human_approval)

    print(f"\n  Verdicts:           {verdict_counts}")
    print(f"  By domain:          {domain_counts}")
    print(f"  Requiring approval: {approval_count} / {len(decisions)}")
    print(f"  Elapsed:            {elapsed_sec:.1f}s")

    # Write execution report
    _write_report(decisions, pred_counts, bus.run_id, start_ts, end_ts, elapsed_sec, verdict_counts, domain_counts, approval_count)

    logger.info("\n✅ Stage 10 Multi-Agent Decision Intelligence: COMPLETE")
    logger.info("   Decisions:    %d", len(decisions))
    logger.info("   Report:       %s", REPORT_PATH)


def _write_report(decisions, pred_counts, run_id, start_ts, end_ts, elapsed, verdict_counts, domain_counts, approval_count):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Count critic challenges
    challenged = sum(1 for d in decisions if d.critic_challenge is not None)

    # Find most recently created audit log
    audit_logs = sorted(DOCS_DIR.glob("decision_audit_*.json"), reverse=True)
    audit_log_ref = audit_logs[0].name if audit_logs else "decision_audit_*.json"

    lines = [
        "# Stage 10 Multi-Agent Decision Intelligence — Execution Report",
        "",
        f"**Execution Timestamp:** `{start_ts.isoformat()}`  ",
        f"**Overall Status:** 🟢 **STAGE 10 AGENT SYSTEM OPERATIONAL**  ",
        f"**run_id:** `{run_id}`  ",
        "",
        "---",
        "",
        "## 1. Prediction Store Input",
        "",
        "| Prediction Table | Rows Available |",
        "|---|---|",
    ]
    for label, cnt in pred_counts.items():
        lines.append(f"| {label} | **{cnt:,}** |")

    lines += [
        "",
        "---",
        "",
        "## 2. Agent Pipeline Results",
        "",
        f"- **Total Decisions Produced:** {len(decisions)}",
        f"- **CriticAgent Challenges Raised:** {challenged}",
        f"- **Requiring Human Approval:** {approval_count} / {len(decisions)}",
        f"- **Elapsed Time:** {elapsed:.1f}s",
        "",
        "### Decisions by Domain",
        "",
        "| Domain | Count |",
        "|---|---|",
    ]
    for domain, cnt in domain_counts.items():
        lines.append(f"| `{domain}` | {cnt} |")

    lines += [
        "",
        "### Decisions by Verdict",
        "",
        "| Verdict | Count |",
        "|---|---|",
    ]
    for verdict, cnt in verdict_counts.items():
        lines.append(f"| `{verdict}` | {cnt} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Sample Decisions",
        "",
        "| Domain | Entity | Action (truncated) | Confidence | Risk | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for d in decisions[:20]:
        action_short = d.recommended_action[:50] + "..." if len(d.recommended_action) > 50 else d.recommended_action
        lines.append(
            f"| `{d.domain.value}` | `{d.entity_id}` | {action_short} | "
            f"{d.confidence_score:.1%} | {d.risk_level.value} | `{d.final_verdict.value}` |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Audit Log",
        "",
        f"- **JSON Audit Log:** `docs/agents/{audit_log_ref}`",
        "- **DB Table:** `analytics.agent_decisions`",
        "",
        "---",
        "",
        f"*Generated: {end_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Execution report written to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
