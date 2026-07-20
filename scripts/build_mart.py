"""CLI: build mart_conditions_hourly from fact_hourly in the DuckDB database.

    python scripts/build_mart.py

Requires fact_hourly to exist (run scripts/build_fact_hourly.py first). Writes
the DuckDB table mart_conditions_hourly and a Parquet copy in data/processed.
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

    n = mart.build_from_duckdb(Path(args.duckdb), Path(args.processed_dir))
    print(f"mart_conditions_hourly: {n:,} rows -> {args.duckdb} "
          f"+ {args.processed_dir}/mart_conditions_hourly.parquet")


if __name__ == "__main__":
    main()
