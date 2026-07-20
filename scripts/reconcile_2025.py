"""CLI: reconcile completed-2025 fact_hourly totals against official figures.

    python scripts/reconcile_2025.py

Reads data/processed/fact_hourly.parquet, prints the comparison table, and
exits non-zero if any metric falls outside tolerance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smardpipe import reconcile  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Reconcile 2025 vs official.")
    ap.add_argument("--parquet", default="data/processed/fact_hourly.parquet")
    args = ap.parse_args()

    fact = pd.read_parquet(args.parquet)
    report = reconcile.reconcile(fact)

    pd.set_option("display.width", 200)
    print(report.to_string(index=False))
    print(f"\nOfficial source: {reconcile.OFFICIAL_SOURCE}")

    if not report["pass"].all():
        print("\nRECONCILIATION FAILED", file=sys.stderr)
        raise SystemExit(1)
    print("\nAll metrics within tolerance.")


if __name__ == "__main__":
    main()
