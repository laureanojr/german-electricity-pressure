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
    ap.add_argument(
        "--emit-fixture", metavar="PATH",
        help="write the 2025 reconcile columns to PATH (parquet) and exit; "
             "regenerates tests/fixtures/fact_2025_reconcile.parquet for the CI gate",
    )
    args = ap.parse_args()

    fact = pd.read_parquet(args.parquet)

    if args.emit_fixture:
        # Same slice the CI gate reconciles: completed 2025, needed columns only.
        slice_ = (
            fact[fact["year"] == 2025]
            .sort_values("hour_ms")[list(reconcile.RECONCILE_COLUMNS)]
        )
        slice_.to_parquet(args.emit_fixture, compression="zstd", index=False)
        print(f"wrote {len(slice_)} rows to {args.emit_fixture}")
        return

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
