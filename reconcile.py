"""
reconcile.py
------------
SQL-based payout reconciliation engine.
Loads transaction CSV into SQLite and runs complex SQL queries
to compute monthly payouts, rank partners, and detect variances.
"""

import sqlite3
import csv
import os
from datetime import datetime


DB_PATH = "finops.db"
DATA_PATH = os.path.join("data", "sample_transactions.csv")


def load_data_to_db(conn: sqlite3.Connection) -> int:
    """Load CSV transaction data into SQLite database."""
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("""
        CREATE TABLE transactions (
            transaction_id  TEXT PRIMARY KEY,
            partner_id      TEXT NOT NULL,
            partner_name    TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            category        TEXT NOT NULL,
            actual_amount   REAL NOT NULL,
            expected_amount REAL NOT NULL,
            status          TEXT NOT NULL
        )
    """)

    with open(DATA_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["transaction_id"], r["partner_id"], r["partner_name"],
                r["transaction_date"], r["category"],
                float(r["actual_amount"]), float(r["expected_amount"]),
                r["status"]
            )
            for r in reader
        ]

    cursor.executemany(
        "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"[+] Loaded {len(rows)} transactions into database.\n")
    return len(rows)


def monthly_payout_summary(conn: sqlite3.Connection) -> list[dict]:
    """
    Complex SQL Query 1:
    Monthly payout per partner with variance, percentage difference,
    and running total using window functions.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            partner_name,
            strftime('%Y-%m', transaction_date)          AS month,
            COUNT(*)                                      AS txn_count,
            ROUND(SUM(actual_amount), 2)                 AS total_actual,
            ROUND(SUM(expected_amount), 2)               AS total_expected,
            ROUND(SUM(actual_amount) - SUM(expected_amount), 2) AS variance,
            ROUND(
                (SUM(actual_amount) - SUM(expected_amount))
                / NULLIF(SUM(expected_amount), 0) * 100, 2
            )                                             AS variance_pct,
            ROUND(SUM(SUM(actual_amount)) OVER (
                PARTITION BY partner_name
                ORDER BY strftime('%Y-%m', transaction_date)
            ), 2)                                         AS running_total
        FROM transactions
        GROUP BY partner_name, month
        ORDER BY partner_name, month
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def category_cost_allocation(conn: sqlite3.Connection) -> list[dict]:
    """
    Complex SQL Query 2:
    Cost allocation by category — share of total spend,
    average transaction size, and discrepancy rate.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            category,
            COUNT(*)                                          AS txn_count,
            ROUND(SUM(actual_amount), 2)                     AS total_payout,
            ROUND(SUM(actual_amount) * 100.0 /
                SUM(SUM(actual_amount)) OVER (), 2)          AS pct_of_total,
            ROUND(AVG(actual_amount), 2)                     AS avg_txn_size,
            SUM(CASE WHEN actual_amount != expected_amount
                THEN 1 ELSE 0 END)                           AS discrepancy_count,
            ROUND(SUM(CASE WHEN actual_amount != expected_amount
                THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)   AS discrepancy_rate_pct
        FROM transactions
        GROUP BY category
        ORDER BY total_payout DESC
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def partner_ranking(conn: sqlite3.Connection) -> list[dict]:
    """
    Complex SQL Query 3:
    Rank partners by total payout volume using RANK() window function,
    and flag partners with any discrepancies.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            partner_name,
            ROUND(SUM(actual_amount), 2)                AS total_payout,
            RANK() OVER (ORDER BY SUM(actual_amount) DESC) AS payout_rank,
            SUM(CASE WHEN actual_amount != expected_amount
                THEN 1 ELSE 0 END)                       AS discrepancy_count,
            CASE WHEN SUM(CASE WHEN actual_amount != expected_amount
                THEN 1 ELSE 0 END) > 0
                THEN 'FLAG' ELSE 'CLEAR' END             AS flag_status
        FROM transactions
        GROUP BY partner_name
        ORDER BY payout_rank
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def print_table(data: list[dict], title: str) -> None:
    if not data:
        print("No data.\n")
        return
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    headers = list(data[0].keys())
    col_w = {h: max(len(h), max(len(str(r[h])) for r in data)) for h in headers}
    header_row = "  ".join(h.ljust(col_w[h]) for h in headers)
    print(header_row)
    print("-" * len(header_row))
    for row in data:
        print("  ".join(str(row[h]).ljust(col_w[h]) for h in headers))
    print()


def run_reconciliation() -> tuple[sqlite3.Connection, list[dict]]:
    conn = sqlite3.connect(DB_PATH)
    load_data_to_db(conn)

    monthly = monthly_payout_summary(conn)
    print_table(monthly, "Monthly Payout Summary with Running Totals")

    allocation = category_cost_allocation(conn)
    print_table(allocation, "Category-wise Cost Allocation")

    ranking = partner_ranking(conn)
    print_table(ranking, "Partner Payout Ranking & Flag Status")

    return conn, monthly


if __name__ == "__main__":
    conn, _ = run_reconciliation()
    conn.close()
