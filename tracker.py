"""
tracker.py
----------
SLA compliance tracker.
Monitors daily processing targets, calculates completion rates,
and generates progress alerts for reporting cycles.
"""

import sqlite3
import csv
import os
from datetime import datetime, date, timedelta


REPORTS_DIR = "reports"
TRACKER_CSV = os.path.join(REPORTS_DIR, "daily_tracker.csv")
PROGRESS_TXT = os.path.join(REPORTS_DIR, "sla_progress_report.txt")

DAILY_TARGET = 5        # transactions expected per working day
SLA_THRESHOLD = 80.0    # minimum % completion to be SLA-compliant


def get_daily_counts(conn: sqlite3.Connection) -> list[dict]:
    """Fetch transaction counts grouped by date."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            transaction_date                        AS date,
            COUNT(*)                                AS txn_processed,
            SUM(actual_amount)                      AS total_amount,
            SUM(CASE WHEN actual_amount != expected_amount
                THEN 1 ELSE 0 END)                  AS discrepancies
        FROM transactions
        GROUP BY transaction_date
        ORDER BY transaction_date
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def compute_sla(daily_counts: list[dict]) -> list[dict]:
    """Enrich daily counts with SLA compliance status."""
    enriched = []
    for record in daily_counts:
        processed = record["txn_processed"]
        completion_pct = round(processed / DAILY_TARGET * 100, 1)
        sla_status = "COMPLIANT" if completion_pct >= SLA_THRESHOLD else "BREACH"
        shortfall = max(0, DAILY_TARGET - processed)
        enriched.append({
            **record,
            "daily_target":    DAILY_TARGET,
            "completion_pct":  completion_pct,
            "shortfall":       shortfall,
            "sla_status":      sla_status,
        })
    return enriched


def run_tracker(conn: sqlite3.Connection) -> list[dict]:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    daily_counts = get_daily_counts(conn)
    sla_data = compute_sla(daily_counts)

    # Write tracker CSV
    if sla_data:
        fieldnames = list(sla_data[0].keys())
        with open(TRACKER_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sla_data)

    # Compute overall stats
    total_days = len(sla_data)
    compliant_days = sum(1 for r in sla_data if r["sla_status"] == "COMPLIANT")
    breach_days = total_days - compliant_days
    overall_sla_pct = round(compliant_days / total_days * 100, 1) if total_days else 0
    total_processed = sum(r["txn_processed"] for r in sla_data)
    total_discrepancies = sum(r["discrepancies"] for r in sla_data)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write progress report
    with open(PROGRESS_TXT, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("       SLA COMPLIANCE PROGRESS REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated      : {timestamp}\n")
        f.write(f"Reporting Period : {sla_data[0]['date']} to {sla_data[-1]['date']}\n")
        f.write(f"Daily Target   : {DAILY_TARGET} transactions/day\n")
        f.write(f"SLA Threshold  : {SLA_THRESHOLD}% completion\n\n")
        f.write("Overall Performance:\n")
        f.write(f"  Total Days Tracked   : {total_days}\n")
        f.write(f"  Compliant Days       : {compliant_days}\n")
        f.write(f"  SLA Breach Days      : {breach_days}\n")
        f.write(f"  Overall SLA Rate     : {overall_sla_pct}%\n")
        f.write(f"  Total Processed      : {total_processed} transactions\n")
        f.write(f"  Total Discrepancies  : {total_discrepancies}\n\n")

        if overall_sla_pct < SLA_THRESHOLD:
            f.write("  ⚠ ALERT: Overall SLA below threshold — escalation recommended.\n\n")
        else:
            f.write("  ✓ SLA target met for this reporting cycle.\n\n")

        f.write("Daily Breakdown:\n")
        f.write("-" * 60 + "\n")
        for r in sla_data:
            flag = "⚠" if r["sla_status"] == "BREACH" else "✓"
            f.write(
                f"  {flag} {r['date']} | "
                f"Processed: {r['txn_processed']}/{DAILY_TARGET} | "
                f"{r['completion_pct']}% | {r['sla_status']}\n"
            )

    # Console output
    print(f"\n{'='*60}")
    print("  SLA TRACKER")
    print(f"{'='*60}")
    print(f"  Period         : {sla_data[0]['date']} → {sla_data[-1]['date']}")
    print(f"  Overall SLA    : {overall_sla_pct}%  "
          f"({'✓ COMPLIANT' if overall_sla_pct >= SLA_THRESHOLD else '⚠ BREACH'})")
    print(f"  Compliant Days : {compliant_days}/{total_days}")
    print(f"  Breach Days    : {breach_days}")
    print(f"\n  Tracker CSV    → {TRACKER_CSV}")
    print(f"  Progress report → {PROGRESS_TXT}\n")

    return sla_data


if __name__ == "__main__":
    from reconcile import run_reconciliation
    conn, _ = run_reconciliation()
    run_tracker(conn)
    conn.close()
