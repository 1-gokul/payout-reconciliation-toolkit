"""
audit.py
--------
Discrepancy detection engine and escalation logger.
Categorizes anomalies by severity, timestamps records,
and outputs audit-ready CSVs for stakeholder review.
"""

import sqlite3
import csv
import os
from datetime import datetime


LOGS_DIR = "logs"
ESCALATION_LOG = os.path.join(LOGS_DIR, "escalation_log.csv")
AUDIT_SUMMARY = os.path.join(LOGS_DIR, "audit_summary.txt")

SEVERITY_THRESHOLDS = {
    "HIGH":   15.0,   # variance > 15%
    "MEDIUM": 5.0,    # variance 5–15%
    "LOW":    0.01,   # any variance < 5%
}


def get_severity(variance_pct: float) -> str:
    abs_var = abs(variance_pct)
    if abs_var > SEVERITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif abs_var > SEVERITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    else:
        return "LOW"


def detect_discrepancies(conn: sqlite3.Connection) -> list[dict]:
    """Fetch all transactions where actual != expected."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            transaction_id,
            partner_name,
            transaction_date,
            category,
            actual_amount,
            expected_amount,
            ROUND(actual_amount - expected_amount, 2)            AS variance,
            ROUND((actual_amount - expected_amount)
                / NULLIF(expected_amount, 0) * 100, 2)           AS variance_pct
        FROM transactions
        WHERE actual_amount != expected_amount
        ORDER BY ABS(actual_amount - expected_amount) DESC
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def run_audit(conn: sqlite3.Connection) -> list[dict]:
    os.makedirs(LOGS_DIR, exist_ok=True)
    discrepancies = detect_discrepancies(conn)

    if not discrepancies:
        print("[✓] Audit complete. No discrepancies found.")
        return []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    enriched = []
    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for record in discrepancies:
        severity = get_severity(record["variance_pct"])
        severity_counts[severity] += 1
        enriched.append({
            **record,
            "severity":      severity,
            "flagged_at":    timestamp,
            "resolution":    "PENDING"
        })

    # Write escalation log CSV
    fieldnames = list(enriched[0].keys())
    with open(ESCALATION_LOG, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    # Write human-readable audit summary
    total_variance = sum(abs(r["variance"]) for r in enriched)
    with open(AUDIT_SUMMARY, "w") as f:
        f.write("=" * 60 + "\n")
        f.write("         FINOPS AUDIT SUMMARY REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated : {timestamp}\n")
        f.write(f"Total Discrepancies : {len(enriched)}\n")
        f.write(f"Total Variance Amount : ₹{total_variance:,.2f}\n\n")
        f.write("Severity Breakdown:\n")
        for sev, count in severity_counts.items():
            f.write(f"  {sev:<8} : {count} record(s)\n")
        f.write("\nDiscrepancy Details:\n")
        f.write("-" * 60 + "\n")
        for r in enriched:
            f.write(
                f"[{r['severity']:<6}] {r['transaction_id']} | "
                f"{r['partner_name']:<18} | "
                f"Variance: ₹{r['variance']:>10,.2f} ({r['variance_pct']:>+.1f}%)\n"
            )

    # Console output
    print(f"\n{'='*60}")
    print("  AUDIT RESULTS")
    print(f"{'='*60}")
    print(f"  Discrepancies Found : {len(enriched)}")
    print(f"  Total Variance      : ₹{total_variance:,.2f}")
    print(f"  HIGH severity       : {severity_counts['HIGH']}")
    print(f"  MEDIUM severity     : {severity_counts['MEDIUM']}")
    print(f"  LOW severity        : {severity_counts['LOW']}")
    print(f"\n  Escalation log  → {ESCALATION_LOG}")
    print(f"  Audit summary   → {AUDIT_SUMMARY}\n")

    return enriched


if __name__ == "__main__":
    from reconcile import run_reconciliation
    conn, _ = run_reconciliation()
    run_audit(conn)
    conn.close()
