# Partner Payout Reconciliation & FinOps Reporting Toolkit

A Python-based FinOps pipeline for reconciling partner payouts, detecting financial discrepancies, tracking SLA compliance, and auto-generating stakeholder reports — built to simulate real-world financial operations workflows.

## Overview

| Challenge | Module |
|---|---|
| Reconcile monthly partner payouts using SQL | `reconcile.py` |
| Detect discrepancies and log escalations by severity | `audit.py` |
| Track daily processing targets and SLA compliance | `tracker.py` |
| Auto-generate stakeholder payout reports | `report_generator.py` |

## Project Structure

```
payout-reconciliation-toolkit/
├── main.py                          # Full pipeline entry point
├── reconcile.py                     # SQL-based payout reconciliation engine
├── audit.py                         # Discrepancy detection & escalation logger
├── tracker.py                       # SLA compliance tracker & progress reporter
├── report_generator.py              # Automated stakeholder report generator
├── requirements.txt                 # No external dependencies (stdlib only)
│
├── data/
│   └── sample_transactions.csv      # Sample B2B partner transaction data
│
├── reports/                         # Auto-created at runtime
│   ├── payout_summary.csv
│   ├── variance_analysis.csv
│   ├── daily_tracker.csv
│   └── stakeholder_report.txt
│
└── logs/                            # Auto-created at runtime
    ├── escalation_log.csv
    └── audit_summary.txt
```

## Usage

```bash
# Run full pipeline
python main.py

# Run individual modules
python main.py --module reconcile
python main.py --module audit
python main.py --module tracker
python main.py --module report
```

## Key SQL Features Used

- **Window functions** — `RANK()`, running totals with `SUM() OVER()`
- **Aggregations** — `SUM`, `AVG`, `COUNT`, `MIN`, `MAX` grouped by partner and category
- **Conditional aggregation** — `SUM(CASE WHEN ...)` for discrepancy rates
- **Variance calculation** — percentage variance with `NULLIF` guard
- **Cost allocation** — percentage share of total using `SUM() OVER()`

## Requirements

No external libraries required. Uses Python standard library only:
- `sqlite3` — in-memory SQL engine
- `csv` — data I/O
- `os`, `datetime`, `argparse` — utilities
