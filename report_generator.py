"""
report_generator.py
-------------------
Automated stakeholder report generator.
Produces structured payout summaries, variance analysis,
and partner-level breakdowns — eliminating manual Excel reporting.
"""

import sqlite3
import csv
import os
from datetime import datetime


REPORTS_DIR = "reports"
PAYOUT_CSV   = os.path.join(REPORTS_DIR, "payout_summary.csv")
VARIANCE_CSV = os.path.join(REPORTS_DIR, "variance_analysis.csv")
FULL_REPORT  = os.path.join(REPORTS_DIR, "stakeholder_report.txt")


def get_payout_summary(conn: sqlite3.Connection) -> list[dict]:
    """Partner-level payout breakdown for the full period."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            partner_id,
            partner_name,
            COUNT(*)                                        AS total_transactions,
            ROUND(SUM(actual_amount), 2)                   AS total_paid,
            ROUND(SUM(expected_amount), 2)                 AS total_expected,
            ROUND(SUM(actual_amount) - SUM(expected_amount), 2) AS net_variance,
            ROUND(MIN(actual_amount), 2)                   AS min_txn,
            ROUND(MAX(actual_amount), 2)                   AS max_txn,
            ROUND(AVG(actual_amount), 2)                   AS avg_txn
        FROM transactions
        GROUP BY partner_id, partner_name
        ORDER BY total_paid DESC
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_variance_analysis(conn: sqlite3.Connection) -> list[dict]:
    """Transaction-level variance breakdown — only flagged records."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            transaction_id,
            partner_name,
            category,
            transaction_date,
            ROUND(actual_amount, 2)                                 AS actual,
            ROUND(expected_amount, 2)                               AS expected,
            ROUND(actual_amount - expected_amount, 2)               AS variance,
            ROUND((actual_amount - expected_amount)
                / NULLIF(expected_amount, 0) * 100, 2)              AS variance_pct,
            CASE
                WHEN actual_amount > expected_amount THEN 'OVERPAID'
                WHEN actual_amount < expected_amount THEN 'UNDERPAID'
                ELSE 'MATCHED'
            END                                                     AS variance_type
        FROM transactions
        WHERE actual_amount != expected_amount
        ORDER BY ABS(actual_amount - expected_amount) DESC
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def write_csv(data: list[dict], path: str) -> None:
    if not data:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)


def generate_report(conn: sqlite3.Connection) -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    payout_data   = get_payout_summary(conn)
    variance_data = get_variance_analysis(conn)

    write_csv(payout_data,   PAYOUT_CSV)
    write_csv(variance_data, VARIANCE_CSV)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_paid     = sum(r["total_paid"] for r in payout_data)
    total_expected = sum(r["total_expected"] for r in payout_data)
    net_variance   = round(total_paid - total_expected, 2)
    total_txns     = sum(r["total_transactions"] for r in payout_data)
    overpaid_amt   = sum(r["variance"] for r in variance_data if r["variance_type"] == "OVERPAID")
    underpaid_amt  = sum(r["variance"] for r in variance_data if r["variance_type"] == "UNDERPAID")

    with open(FULL_REPORT, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("         PARTNER PAYOUT — STAKEHOLDER REPORT\n")
        f.write("=" * 65 + "\n")
        f.write(f"  Report Generated : {timestamp}\n")
        f.write(f"  Prepared By      : FinOps Reconciliation System v1.0\n\n")

        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 65 + "\n")
        f.write(f"  Total Partners          : {len(payout_data)}\n")
        f.write(f"  Total Transactions      : {total_txns}\n")
        f.write(f"  Total Amount Paid       : ₹{total_paid:>12,.2f}\n")
        f.write(f"  Total Amount Expected   : ₹{total_expected:>12,.2f}\n")
        f.write(f"  Net Variance            : ₹{net_variance:>12,.2f}\n")
        f.write(f"  Discrepant Transactions : {len(variance_data)}\n")
        f.write(f"  Total Overpaid          : ₹{overpaid_amt:>12,.2f}\n")
        f.write(f"  Total Underpaid         : ₹{underpaid_amt:>12,.2f}\n\n")

        f.write("PARTNER PAYOUT BREAKDOWN\n")
        f.write("-" * 65 + "\n")
        for r in payout_data:
            status = "⚠ VARIANCE" if r["net_variance"] != 0 else "✓ MATCHED"
            f.write(
                f"  {r['partner_name']:<20} | "
                f"Paid: ₹{r['total_paid']:>10,.2f} | "
                f"Variance: ₹{r['net_variance']:>8,.2f} | {status}\n"
            )

        f.write("\nVARIANCE ANALYSIS (FLAGGED TRANSACTIONS)\n")
        f.write("-" * 65 + "\n")
        if variance_data:
            for r in variance_data:
                f.write(
                    f"  {r['transaction_id']} | {r['partner_name']:<18} | "
                    f"{r['variance_type']:<10} | "
                    f"₹{r['variance']:>+10,.2f} ({r['variance_pct']:>+.1f}%)\n"
                )
        else:
            f.write("  No variances detected.\n")

        f.write("\nOUTPUT FILES\n")
        f.write("-" * 65 + "\n")
        f.write(f"  Payout CSV      : {PAYOUT_CSV}\n")
        f.write(f"  Variance CSV    : {VARIANCE_CSV}\n")
        f.write(f"  Full Report     : {FULL_REPORT}\n")

    print(f"\n{'='*60}")
    print("  STAKEHOLDER REPORT GENERATED")
    print(f"{'='*60}")
    print(f"  Total Paid     : ₹{total_paid:,.2f}")
    print(f"  Net Variance   : ₹{net_variance:,.2f}")
    print(f"  Discrepancies  : {len(variance_data)} transactions")
    print(f"\n  Report saved   → {FULL_REPORT}")
    print(f"  Payout CSV     → {PAYOUT_CSV}")
    print(f"  Variance CSV   → {VARIANCE_CSV}\n")


if __name__ == "__main__":
    from reconcile import run_reconciliation
    conn, _ = run_reconciliation()
    generate_report(conn)
    conn.close()
