"""Query layer for the pressure dashboard.

Pure functions: each takes an open DuckDB connection plus the current filter
selection and returns a pandas DataFrame. No Streamlit in here, so the SQL is
unit-testable against a small synthetic database (see tests/test_dashboard_queries.py)
without the real, gitignored gep.duckdb.

Season is defined exactly as in sql/mart_conditions_hourly.sql (winter = DJF,
spring = MAM, summer = JJA, autumn = SON) and derived from month wherever a table
doesn't already carry a season column (fact_forecast_hourly doesn't).

Filters are lists of validated values, never raw strings from the UI: years are
coerced to int and seasons are checked against SEASONS, so the IN-lists spliced
into SQL can't carry anything the caller didn't choose.
"""

from __future__ import annotations

from collections.abc import Iterable

import duckdb
import pandas as pd

YEARS = tuple(range(2019, 2026))
SEASONS = ("winter", "spring", "summer", "autumn")

# month -> season, matching sql/mart_conditions_hourly.sql. Used to filter and
# group forecast rows, which have month but no season column.
_SEASON_CASE = (
    "CASE WHEN month IN (12,1,2) THEN 'winter' "
    "WHEN month IN (3,4,5) THEN 'spring' "
    "WHEN month IN (6,7,8) THEN 'summer' ELSE 'autumn' END"
)


def _year_list(years: Iterable[int]) -> str:
    vals = sorted({int(y) for y in years})
    if not vals:
        vals = list(YEARS)
    return ", ".join(str(v) for v in vals)


def _season_list(seasons: Iterable[str]) -> str:
    vals = [s for s in seasons if s in SEASONS] or list(SEASONS)
    return ", ".join(f"'{s}'" for s in vals)


# --- Residual load -------------------------------------------------------

def residual_duration(con: duckdb.DuckDBPyConnection, years, max_points=600) -> pd.DataFrame:
    """Load-duration-style curve of residual load, one series per year.

    pct_hours is the share of the year's hours at or above that residual, so the
    curve reads left (peak) to right (trough). Downsampled to ~max_points per
    year to keep the chart light; the peak and trough rows are always kept.
    """
    df = con.execute(f"""
        SELECT
            year,
            100.0 * (row_number() OVER (PARTITION BY year ORDER BY residual_load DESC) - 1)
                / count(*) OVER (PARTITION BY year) AS pct_hours,
            residual_load
        FROM fact_hourly
        WHERE year IN ({_year_list(years)}) AND residual_load IS NOT NULL
        ORDER BY year, pct_hours
    """).df()
    if df.empty:
        return df
    out = []
    for _, g in df.groupby("year", sort=True):
        step = max(1, len(g) // max_points)
        keep = g.iloc[::step]
        # guarantee the endpoints (peak / trough) survive downsampling
        keep = pd.concat([g.iloc[[0]], keep, g.iloc[[-1]]]).drop_duplicates("pct_hours")
        out.append(keep)
    return pd.concat(out, ignore_index=True)


def residual_profile_by_hour(con, years, seasons) -> pd.DataFrame:
    """Average residual by local hour of day for the current filter."""
    return con.execute(f"""
        SELECT hour_local, round(avg(residual_load)) AS avg_residual
        FROM mart_conditions_hourly
        WHERE year IN ({_year_list(years)}) AND season IN ({_season_list(seasons)})
        GROUP BY hour_local ORDER BY hour_local
    """).df()


def residual_metrics(con, years, seasons) -> pd.DataFrame:
    """Headline scalars: peak, median, and hours where residual < 0."""
    return con.execute(f"""
        SELECT
            round(max(residual_load))                          AS peak_mw,
            round(median(residual_load))                       AS median_mw,
            count(*) FILTER (WHERE residual_load < 0)          AS hours_below_zero,
            count(*)                                           AS hours
        FROM mart_conditions_hourly
        WHERE year IN ({_year_list(years)}) AND season IN ({_season_list(seasons)})
    """).df()


# --- Price by pressure ---------------------------------------------------

def price_by_decile(con, years, seasons) -> pd.DataFrame:
    """Price and context by residual-pressure decile for the current filter.

    Deciles are the whole-window NTILE bins baked into the mart; slicing by year
    or season changes which hours populate each bin, not the bin edges.
    """
    return con.execute(f"""
        SELECT
            residual_decile,
            round(median(day_ahead_price), 1)                                     AS median_price,
            round(avg(day_ahead_price), 1)                                        AS mean_price,
            round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1)    AS net_importer_pct,
            round(100.0 * avg(CASE WHEN negative_price_flag THEN 1 ELSE 0 END), 1) AS neg_price_pct,
            round(avg(vre_coverage), 2)                                           AS avg_vre_coverage,
            count(*)                                                              AS hours
        FROM mart_conditions_hourly
        WHERE residual_decile IS NOT NULL AND day_ahead_price IS NOT NULL
          AND year IN ({_year_list(years)}) AND season IN ({_season_list(seasons)})
        GROUP BY residual_decile ORDER BY residual_decile
    """).df()


# --- Import reliance -----------------------------------------------------

def import_by_year(con, years) -> pd.DataFrame:
    """Net-importer days and signed net-import energy (TWh) per year."""
    return con.execute(f"""
        SELECT
            year,
            count(*) FILTER (WHERE net_importer_day) AS net_importer_days,
            round(sum(net_import_mwh) / 1e6, 2)      AS net_import_twh
        FROM mart_daily_summary
        WHERE year IN ({_year_list(years)})
        GROUP BY year ORDER BY year
    """).df()


def import_share_by_hour(con, years, seasons) -> pd.DataFrame:
    """Share of hours in commercial net-import position by local hour."""
    return con.execute(f"""
        SELECT hour_local,
               round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1) AS net_importer_pct
        FROM mart_conditions_hourly
        WHERE year IN ({_year_list(years)}) AND season IN ({_season_list(seasons)})
        GROUP BY hour_local ORDER BY hour_local
    """).df()


def import_share_by_vre_band(con, years, seasons) -> pd.DataFrame:
    """Net-import share by VRE coverage band."""
    return con.execute(f"""
        SELECT
            CASE
                WHEN vre_coverage < 0.2 THEN '<0.2'
                WHEN vre_coverage < 0.4 THEN '0.2-0.4'
                WHEN vre_coverage < 0.6 THEN '0.4-0.6'
                WHEN vre_coverage < 0.8 THEN '0.6-0.8'
                ELSE '>=0.8'
            END AS vre_band,
            count(*) AS hours,
            round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1) AS net_importer_pct
        FROM mart_conditions_hourly
        WHERE year IN ({_year_list(years)}) AND season IN ({_season_list(seasons)})
        GROUP BY vre_band ORDER BY min(vre_coverage)
    """).df()


# --- Forecast accuracy ---------------------------------------------------
# fact_forecast_hourly has no season column, so we derive it from month.

def forecast_mae_overall(con, years, seasons) -> pd.DataFrame:
    """Whole-filter MAE per component (MW) and as % of mean actual."""
    return con.execute(f"""
        SELECT
            round(avg(abs(error_load)))                                    AS mae_load,
            round(100 * avg(abs(error_load)) / avg(actual_load), 1)        AS load_pct,
            round(avg(abs(error_wind)))                                    AS mae_wind,
            round(100 * avg(abs(error_wind)) / avg(actual_wind), 1)        AS wind_pct,
            round(avg(abs(error_solar)))                                   AS mae_solar,
            round(100 * avg(abs(error_solar)) / avg(actual_solar), 1)      AS solar_pct,
            round(avg(abs(error_residual)))                                AS mae_residual,
            round(100 * avg(abs(error_residual)) / avg(actual_residual), 1) AS residual_pct
        FROM fact_forecast_hourly
        WHERE year IN ({_year_list(years)}) AND {_SEASON_CASE} IN ({_season_list(seasons)})
    """).df()


def forecast_mae_by_year(con) -> pd.DataFrame:
    """MAE per component by year (all seasons) — shows the solar trend."""
    return con.execute("""
        SELECT year,
            round(avg(abs(error_load)))     AS mae_load,
            round(avg(abs(error_wind)))     AS mae_wind,
            round(avg(abs(error_solar)))    AS mae_solar,
            round(avg(abs(error_residual))) AS mae_residual
        FROM fact_forecast_hourly
        GROUP BY year ORDER BY year
    """).df()


def forecast_mae_by_month(con, years) -> pd.DataFrame:
    """MAE per component by calendar month for the selected years."""
    return con.execute(f"""
        SELECT month,
            round(avg(abs(error_load)))     AS mae_load,
            round(avg(abs(error_wind)))     AS mae_wind,
            round(avg(abs(error_solar)))    AS mae_solar,
            round(avg(abs(error_residual))) AS mae_residual
        FROM fact_forecast_hourly
        WHERE year IN ({_year_list(years)})
        GROUP BY month ORDER BY month
    """).df()


def forecast_mae_by_hour(con, years, seasons) -> pd.DataFrame:
    """MAE per component by local hour for the current filter."""
    return con.execute(f"""
        SELECT hour_local,
            round(avg(abs(error_load)))     AS mae_load,
            round(avg(abs(error_wind)))     AS mae_wind,
            round(avg(abs(error_solar)))    AS mae_solar,
            round(avg(abs(error_residual))) AS mae_residual
        FROM fact_forecast_hourly
        WHERE year IN ({_year_list(years)}) AND {_SEASON_CASE} IN ({_season_list(seasons)})
        GROUP BY hour_local ORDER BY hour_local
    """).df()
