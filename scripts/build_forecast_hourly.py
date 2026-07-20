"""CLI: build fact_forecast_hourly (day-ahead forecast vs actual).

    python scripts/build_forecast_hourly.py

Requires the forecast series to be downloaded first (re-run
scripts/download_smard.py after pulling this update — it fetches the new
forecast series incrementally). Writes fact_forecast_hourly.parquet and the
DuckDB table fact_forecast_hourly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smardpipe import forecast  # noqa: E402
from smardpipe import series as S  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Build fact_forecast_hourly.")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--processed-dir", default="data/processed")
    ap.add_argument("--duckdb", default="data/processed/gep.duckdb")
    ap.add_argument("--start", default=S.WINDOW_START)
    ap.add_argument("--end", default=S.WINDOW_END)
    args = ap.parse_args()

    fact = forecast.build_forecast_hourly(
        Path(args.raw_dir), start=args.start, end=args.end
    )
    report = forecast.assert_coverage(fact)
    print(report.to_string(index=False))

    forecast.write_outputs(fact, Path(args.processed_dir), Path(args.duckdb))
    print(f"\nfact_forecast_hourly: {len(fact):,} rows -> "
          f"{args.processed_dir} + {args.duckdb}")


if __name__ == "__main__":
    main()
