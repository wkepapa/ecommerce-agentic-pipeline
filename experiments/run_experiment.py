"""Runs the complete lab experiment: sequential vs parallel, failure/retry, security tests,
and prints + saves the observation table.   Usage: python experiments/run_experiment.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import settings
from experiments.observation_table import build_observation_table
from experiments.report_generator import save_report
from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow
from security.security_tests import run_security_suite


def run(query, mode, faults=None):
    return ECommerceWorkflow(query, mode=mode, approval_gate=HumanApprovalGate("auto"), faults=faults).run()


def main(query=settings.DEFAULT_QUERY):
    print("Running sequential baseline ...")
    seq = run(query, "sequential")
    print("Running parallel optimized run ...")
    par = run(query, "parallel")
    print("Running failure/retry scenario (source_b fails once) ...")
    fault = run(query, "parallel", faults={"source_b": 1})
    print("Running security suite ...")
    security = run_security_suite()

    table, rows = build_observation_table(query, seq, par, fault, security)
    report_path = save_report(par, security)
    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (settings.REPORT_DIR / "observation_table.md").write_text(table, encoding="utf-8")
    (settings.REPORT_DIR / "experiment_summary.json").write_text(json.dumps({
        "sequential": seq.metrics.summary(), "parallel": par.metrics.summary(),
        "fault_run": fault.metrics.summary(), "security": security}, indent=2, default=str,
        ensure_ascii=False), encoding="utf-8")

    print("\nOBSERVATION TABLE\n" + table)
    print("\nSECURITY TESTS")
    for r in security:
        print(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['test']}: {r['details']}")
    print(f"\nFull report : {report_path}")
    print(f"Table saved : {settings.REPORT_DIR / 'observation_table.md'}")


if __name__ == "__main__":
    main()
