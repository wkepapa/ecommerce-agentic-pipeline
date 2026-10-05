"""CLI entry point.
Examples:
  python main.py
  python main.py --query "Find laptops under 60k with 16 GB RAM and 512 GB SSD, rating above 4.3"
  python main.py --mode sequential
  python main.py --approval interactive
  python main.py --inject-failure source_b:1 --verbose
"""
import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import settings
from experiments.report_generator import save_report
from orchestration.human_approval import HumanApprovalGate
from orchestration.workflow import ECommerceWorkflow
from security.security_tests import run_security_suite


def parse_faults(items):
    faults = {}
    for item in items or []:
        source, _, times = item.partition(":")
        faults[source] = int(times or 1)
    return faults


def main():
    ap = argparse.ArgumentParser(description="Multi-agent e-commerce recommendation pipeline")
    ap.add_argument("--query", default=settings.DEFAULT_QUERY)
    ap.add_argument("--mode", choices=["parallel", "sequential"], default="parallel")
    ap.add_argument("--approval", choices=["interactive", "auto", "reject"], default="interactive",
                    help="human-in-the-loop mode (default: interactive)")
    ap.add_argument("--inject-failure", action="append", metavar="SOURCE:TIMES",
                    help="make a search source fail N times, e.g. source_b:1")
    ap.add_argument("--max-retries", type=int, default=None)
    ap.add_argument("--security-tests", action="store_true", help="also run the security suite")
    ap.add_argument("--verbose", action="store_true", help="echo log events")
    args = ap.parse_args()

    wf = ECommerceWorkflow(args.query, mode=args.mode, approval_gate=HumanApprovalGate(args.approval),
                           faults=parse_faults(args.inject_failure), max_retries=args.max_retries,
                           verbose=args.verbose)
    ctx = wf.run()
    s, m = ctx.state, ctx.metrics.summary()

    print(f"\nStatus        : {s.status}")
    print(f"Requirements  : { {k: v for k, v in s.requirements.items() if v is not None} }")
    print(f"Agent flow    : {ctx.tracer.flow()}")
    for p in s.ranking[:settings.TOP_N]:
        print(f"  #{p['rank']} {p['name']:<28} ₹{p['price']:>8,.0f}  score {p['score']}")
    print(f"Human decision: {s.human_approval.get('decision', 'n/a')}")
    print(f"Time {m['total_time_s']}s | agents {m['agent_calls']} | tools {m['tool_calls']} | "
          f"retries {m['retries']} | cost {m['cost']['total']} units")
    if s.errors:
        print("Errors        :", *[e.get("error") for e in s.errors], sep="\n  - ")

    security = run_security_suite() if args.security_tests else None
    print(f"Report saved  : {save_report(ctx, security)}")


if __name__ == "__main__":
    main()
