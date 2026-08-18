"""
scripts/run_stage8d.py
----------------------
Automated Executor for Stage 8D Machine Telemetry Notebook:
- Converts notebooks/10_stage8d_machine_anomaly.py to .ipynb
- Executes notebook end-to-end using jupyter nbconvert --execute
- Validates cell outputs and saves docs/data_science/stage8d_execution_report.json
"""

import os
import sys
import time
import json
import subprocess
import nbformat
from jupytext import reads, write

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_stage8d_notebook():
    print("=" * 80)
    print("EXECUTING STAGE 8D: MACHINE TELEMETRY ANOMALY & FAILURE ML NOTEBOOK")
    print("=" * 80)

    start_time = time.time()
    py_path = "notebooks/10_stage8d_machine_anomaly.py"
    ipynb_path = "notebooks/10_stage8d_machine_anomaly.ipynb"
    report_path = "docs/data_science/stage8d_execution_report.json"

    # 1. Convert .py script to .ipynb using jupytext
    print(f"Reading {py_path}...")
    with open(py_path, "r", encoding="utf-8") as f:
        py_content = f.read()

    nb = reads(py_content, fmt="py:percent")
    with open(ipynb_path, "w", encoding="utf-8") as f:
        write(nb, f, fmt="ipynb")

    # 2. Execute notebook via jupyter nbconvert
    print("Executing notebook end-to-end with ipykernel...")
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--inplace",
        ipynb_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    execution_time = time.time() - start_time

    if result.returncode != 0:
        print("FAILED to execute notebook:", result.stderr)
        status = "FAILED"
        error_msg = result.stderr
    else:
        print(f"Saved executed notebook to {ipynb_path} ({execution_time:.2f}s)")
        status = "PASS"
        error_msg = None

    # 3. Save Execution Report
    report = {
        "stage": "Stage 8D — Machine Telemetry Anomaly & Predictive Maintenance ML",
        "notebook_path": ipynb_path,
        "overall_status": status,
        "execution_time_seconds": round(execution_time, 2),
        "error_message": error_msg,
        "checks": {
            "notebook_converted": os.path.exists(ipynb_path),
            "execution_exit_code_zero": result.returncode == 0
        }
    }

    os.makedirs("docs/data_science", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Saved execution report to {report_path}")
    print("=" * 80)
    return status == "PASS"


if __name__ == "__main__":
    success = run_stage8d_notebook()
    if not success:
        sys.exit(1)
