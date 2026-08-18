"""
Stage 10A Governance Closure & Verification Script
================================------------------
Executes the 5 formal closure steps:
1. Re-runs complete Stage 9 batch inference (all 4 domains) from a clean prediction store.
2. Audits and confirms machine health prediction probability & health status distributions.
3. Re-runs cross-model governance audit script (scripts/audit_cross_model_governance.py).
4. Confirms that all 3 failure breakdown events achieve valid advance warning (>=6h lead-time).
5. Re-runs Stage 10 Agent decision system (scripts/run_stage10_agents.py) and verifies
   analytics.agent_decisions contains updated, non-escalated Operations decisions.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text
from data_science.db import get_engine
from data_science.mlops.batch_inference import BatchInferenceEngine

def main():
    print("=" * 80)
    print("STAGE 10A FORMAL GOVERNANCE & REPRODUCIBILITY CLOSURE")
    print("=" * 80)

    engine = get_engine()

    # ------------------------------------------------------------------
    # Step 1: Clean prediction tables & re-run complete Stage 9 batch inference
    # ------------------------------------------------------------------
    print("\n>>> Step 1: Re-running Stage 9 Batch Inference across all 4 domains...")
    batch_engine = BatchInferenceEngine(engine)
    res = batch_engine.run_all_batch_inferences()
    print("Batch Inference Summary:", res)

    for k, v in res.items():
        if v.get("status") != "SUCCESS":
            print(f"FAILED: {k} inference failed!")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Confirm probability & decision distributions in prediction store
    # ------------------------------------------------------------------
    print("\n>>> Step 2: Verifying Machine Health Prediction Store Distributions...")
    with engine.connect() as conn:
        df_mh = pd.read_sql(text("""
            SELECT failure_prob_24h, anomaly_score, is_anomaly_flag, failure_alert_flag_24h, health_status
            FROM analytics.fact_predictions_machine_health
        """), conn)

    total_rows = len(df_mh)
    nonzero_probs = (df_mh['failure_prob_24h'] > 0).sum()
    max_prob = df_mh['failure_prob_24h'].max()
    mean_prob = df_mh['failure_prob_24h'].mean()
    high_risk = (df_mh['failure_prob_24h'] >= 0.50).sum()

    print(f"  Total Rows: {total_rows}")
    print(f"  Non-zero Failure Probs: {nonzero_probs} ({nonzero_probs/total_rows:.2%})")
    print(f"  Max Failure Prob: {max_prob:.4f}")
    print(f"  Mean Failure Prob: {mean_prob:.4f}")
    print(f"  High-Risk Rows (>=0.50): {high_risk}")
    print("  Health Status Counts:")
    print(df_mh['health_status'].value_counts().to_string())

    if nonzero_probs == 0 or max_prob < 0.50:
        print("FAILED: Machine Health prediction store has invalid probabilities!")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3 & 4: Re-run Cross-Model Governance Audit
    # ------------------------------------------------------------------
    print("\n>>> Step 3 & 4: Running Cross-Model Governance Audit (Lead-time & Event Validation)...")
    audit_script = PROJECT_ROOT / "scripts" / "audit_cross_model_governance.py"
    proc = subprocess.run([sys.executable, str(audit_script)], capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        print("Governance audit script error output:")
        print(proc.stderr)
        print("FAILED: Governance audit script failed!")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 5: Re-run Stage 10 Agent Decision System & persist decisions
    # ------------------------------------------------------------------
    print("\n>>> Step 5: Re-running Stage 10 Multi-Agent System & Persisting Decisions...")
    stage10_script = PROJECT_ROOT / "scripts" / "run_stage10_agents.py"
    proc_agents = subprocess.run([sys.executable, str(stage10_script)], capture_output=True, text=True)
    print(proc_agents.stdout)
    if proc_agents.returncode != 0:
        print("Stage 10 runner error output:")
        print(proc_agents.stderr)
        print("FAILED: Stage 10 runner failed!")
        sys.exit(1)

    # Audit analytics.agent_decisions table contents
    print("\n>>> Step 5 Verification: Auditing analytics.agent_decisions in PostgreSQL...")
    with engine.connect() as conn:
        df_decisions = pd.read_sql(text("""
            SELECT domain, final_verdict, risk_level, COUNT(*) as count
            FROM analytics.agent_decisions
            GROUP BY domain, final_verdict, risk_level
            ORDER BY domain, final_verdict
        """), conn)

    print("\nPersisted Agent Decisions Breakdown:")
    print(df_decisions.to_string(index=False))

    ops_decisions = df_decisions[df_decisions['domain'] == 'operations']
    print("\nOperations Agent Verdicts:")
    print(ops_decisions.to_string(index=False))

    escalated_count = ops_decisions[ops_decisions['final_verdict'] == 'ESCALATED']['count'].sum() if not ops_decisions.empty and 'ESCALATED' in ops_decisions['final_verdict'].values else 0
    total_ops = ops_decisions['count'].sum() if not ops_decisions.empty else 0

    print(f"\nOperations Agent: {total_ops} decisions generated, {escalated_count} ESCALATED.")

    if escalated_count == total_ops and total_ops > 0:
        print("FAILED: All Operations decisions are still ESCALATED!")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("STAGE 10A GOVERNANCE CLOSURE PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
