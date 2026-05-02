"""
main.py
-------
Entry point for the Partner Payout Reconciliation & FinOps Reporting Toolkit.
Runs the full pipeline: load → reconcile → audit → track SLA → generate report.

Usage:
    python main.py
    python main.py --module reconcile
    python main.py --module audit
    python main.py --module tracker
    python main.py --module report
"""

import sys
import argparse
import sqlite3

from reconcile        import run_reconciliation
from audit            import run_audit
from tracker          import run_tracker
from report_generator import generate_report


BANNER = """
╔══════════════════════════════════════════════════════════╗
║   Partner Payout Reconciliation & FinOps Reporting v1.0 ║
╚══════════════════════════════════════════════════════════╝
"""


def run_all() -> None:
    print(BANNER)

    print("[ STEP 1 ] Loading & Reconciling Transactions...")
    conn, _ = run_reconciliation()

    print("[ STEP 2 ] Running Discrepancy Audit...")
    run_audit(conn)

    print("[ STEP 3 ] Computing SLA Compliance...")
    run_tracker(conn)

    print("[ STEP 4 ] Generating Stakeholder Report...")
    generate_report(conn)

    conn.close()
    print("\n[✓] Full pipeline complete. Check /reports and /logs for outputs.")


def run_module(module: str) -> None:
    print(BANNER)
    conn, _ = run_reconciliation()
    if module == "reconcile":
        pass  # already done above
    elif module == "audit":
        run_audit(conn)
    elif module == "tracker":
        run_tracker(conn)
    elif module == "report":
        generate_report(conn)
    else:
        print(f"Unknown module: {module}")
        print("Options: reconcile | audit | tracker | report")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FinOps Payout Reconciliation Toolkit"
    )
    parser.add_argument(
        "--module",
        choices=["reconcile", "audit", "tracker", "report"],
        help="Run a specific module only (default: run all)"
    )
    args = parser.parse_args()

    if args.module:
        run_module(args.module)
    else:
        run_all()
