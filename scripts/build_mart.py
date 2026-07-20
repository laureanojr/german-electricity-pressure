"""CLI: build the marts (conditions + daily summary) from fact_hourly.

    python scripts/build_mart.py

Requires fact_hourly to exist (run scripts/build_fact_hourly.py first). Writes
DuckDB tables mart_conditions_hourly and mart_daily_summary plus Parquet copies
in data/processed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smardpipe import mart  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Build mart_conditions_hourly.")
    ap.add_argument("--duckdb", default="data/processed/gep.duckdb")
    ap.add_argument("--processed-dir", default="data/processed")
    args = ap.parse_args()

    counts = mart.build_from_duckdb(Path(args.duckdb), Path(args.processed_dir))
    for table, n in counts.items():
        print(f"{table}: {n:,} rows -> {args.duckdb} "
              f"+ {args.processed_dir}/{table}.parquet")


if __name__ == "__main__":
    main()
