"""CLI: build fact_hourly from cached raw files, assert coverage, write outputs.

    python scripts/build_fact_hourly.py

Writes data/processed/fact_hourly.parquet and loads it into
data/processed/gep.duckdb as table ``fact_hourly``. Exits non-zero if the
coverage check fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smardpipe import build  # noqa: E402
from smardpipe import series as S  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Build fact_hourly.")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--processed-dir", default="data/processed")
    ap.add_argument("--duckdb", default="data/processed/gep.duckdb")
    ap.add_argument("--start", default=S.WINDOW_START)
    ap.add_argument("--end", default=S.WINDOW_END)
    args = ap.parse_args()

    fact = build.build_fact_hourly(
        Path(args.raw_dir), start=args.start, end=args.end
    )
    report = build.assert_coverage(fact)
    print(report.to_string(index=False))

    build.write_outputs(fact, Path(args.processed_dir), Path(args.duckdb))
    print(f"\nfact_hourly: {len(fact):,} rows -> {args.processed_dir} + {args.duckdb}")


if __name__ == "__main__":
    main()
