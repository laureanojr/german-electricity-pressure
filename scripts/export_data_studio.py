"""Export dashboard-ready CSVs for the Data Studio report.

(Data Studio is Google's free reporting tool — the product Google briefly called
Looker Studio from 2022 and renamed back to Data Studio in April 2026. The
enterprise "Looker" is a different product.)

Writes to exports/data_studio/. Two grains, on purpose:

  Detail tables (Data Studio aggregates and filters these live):
    conditions_hourly.csv  one row per UTC hour, from mart_conditions_hourly —
                           the base for Page 1/2 charts and every filter.
    forecast_hourly.csv    one row per UTC hour, from fact_forecast_hourly, with
                           abs_error_* precomputed so MAE = AVG(abs_error_x).

  Precomputed summaries (things a BI tool can't compute reliably over a live table):
    price_by_decile.csv    10 rows with the MEDIAN day-ahead price per residual
                           decile — Data Studio has no dependable live median, so
                           it's done in SQL here.
    residual_duration_by_year.csv  the duration curve (a per-year sort), which a
                           BI tool can't produce from an unordered table.
    coverage_by_year.csv   completeness for the Page 3 data-notes panel.
    daily_summary.csv      per-day rollup for net-importer days / TWh headlines.

Run (pipeline venv):  python scripts/export_data_studio.py
exports/ is gitignored — this is a reproducible build step, not a data mirror.
Source: Bundesnetzagentur | SMARD.de (CC BY 4.0).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "processed" / "gep.duckdb"
DEFAULT_OUT = ROOT / "exports" / "data_studio"

# Readable Weekend/Weekday label used as a filter dimension across the report.
_DAY_TYPE = "CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END"
# season from month, matching sql/mart_conditions_hourly.sql (forecast table has none).
_SEASON = (
    "CASE WHEN month IN (12,1,2) THEN 'winter' WHEN month IN (3,4,5) THEN 'spring' "
    "WHEN month IN (6,7,8) THEN 'summer' ELSE 'autumn' END"
)

EXPORTS: dict[str, str] = {
    # --- detail tables (live aggregation + filtering in Data Studio) ---
    "conditions_hourly": f"""
        SELECT
            date_local, year, month, hour_local, season,
            {_DAY_TYPE}                                   AS day_type,
            residual_load, vre_coverage, day_ahead_price,
            residual_decile, price_decile,
            net_import,
            CAST(net_import_flag AS INT)                  AS net_importer,
            CAST(negative_price_flag AS INT)              AS negative_price
        FROM mart_conditions_hourly
        ORDER BY date_local, hour_local
    """,
    "forecast_hourly": f"""
        SELECT
            date_local, year, month, hour_local,
            {_SEASON}        AS season,
            {_DAY_TYPE}      AS day_type,
            actual_load, actual_wind, actual_solar, actual_residual,
            error_load, error_wind, error_solar, error_residual,
            abs(error_load)     AS abs_error_load,
            abs(error_wind)     AS abs_error_wind,
            abs(error_solar)    AS abs_error_solar,
            abs(error_residual) AS abs_error_residual
        FROM fact_forecast_hourly
        ORDER BY date_local, hour_local
    """,
    # --- precomputed summaries ---
    "price_by_decile": """
        SELECT
            residual_decile,
            round(median(day_ahead_price), 1)                                     AS median_price,
            round(avg(day_ahead_price), 1)                                        AS mean_price,
            round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1)     AS net_importer_pct,
            round(100.0 * avg(CASE WHEN negative_price_flag THEN 1 ELSE 0 END), 1) AS neg_price_pct,
            round(avg(vre_coverage), 2)                                           AS avg_vre_coverage,
            count(*)                                                              AS hours
        FROM mart_conditions_hourly
        WHERE residual_decile IS NOT NULL AND day_ahead_price IS NOT NULL
        GROUP BY residual_decile ORDER BY residual_decile
    """,
    # Duration curve: per-year descending sort, thinned to ~200 points/year, with
    # the trough (rn = n) always kept. row_number gives the exceedance position.
    "residual_duration_by_year": """
        WITH ranked AS (
            SELECT year, residual_load,
                row_number() OVER (PARTITION BY year ORDER BY residual_load DESC) AS rn,
                count(*)     OVER (PARTITION BY year)                             AS n
            FROM fact_hourly
            WHERE residual_load IS NOT NULL
        )
        SELECT year,
               round(100.0 * (rn - 1) / n, 3) AS pct_hours,
               residual_load
        FROM ranked
        WHERE rn % 44 = 1 OR rn = n
        ORDER BY year, pct_hours
    """,
    "coverage_by_year": """
        SELECT
            year,
            count(*)                                            AS hours,
            count(*) FILTER (WHERE day_ahead_price IS NULL)     AS missing_price_hours,
            count(*) FILTER (WHERE residual_load IS NULL)       AS missing_residual_hours,
            count(*) FILTER (WHERE net_import IS NULL)          AS missing_net_import_hours
        FROM fact_hourly
        GROUP BY year ORDER BY year
    """,
    "daily_summary": """
        SELECT
            date_local, year, month, season, dow, is_weekend, n_hours,
            residual_load_mwh, vre_coverage,
            avg_price, min_price, max_price, negative_price_hours,
            net_import_mwh, net_import_hours, net_importer_day
        FROM mart_daily_summary
        ORDER BY date_local
    """,
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Export CSVs for the Data Studio report.")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db, read_only=True)

    for name, sql in EXPORTS.items():
        path = out / f"{name}.csv"
        con.execute(
            f"COPY ({sql}) TO '{path}' (HEADER, FORMAT CSV)"
        )
        rows = con.execute(f"SELECT count(*) FROM ({sql})").fetchone()[0]
        print(f"{name:<28} {rows:>6} rows -> {path}")


if __name__ == "__main__":
    main()
