"""Smoke tests for the dashboard query layer.

These build a tiny synthetic gep.duckdb in memory (no real, gitignored data) and
run every query function, so CI catches broken SQL, renamed columns, or a filter
that stops matching. They check shape and that filters bite — not exact
analytical values (that's what test_reconcile_real_2025.py and findings.md do).
"""

from __future__ import annotations

import duckdb
import pytest

from dashboard import queries as q


@pytest.fixture()
def con():
    """In-memory DB with the four tables the dashboard reads, minimally populated.

    Two years x two seasons x a couple of hours, enough to exercise grouping and
    the year/season filters. Deciles are stubbed 1..10 across the rows so
    price_by_decile has bins to group on.
    """
    c = duckdb.connect()
    c.execute("""
        CREATE TABLE fact_hourly AS
        SELECT * FROM (VALUES
            (2019, 1, 10, 40000.0),
            (2019, 7, 13, 20000.0),
            (2025, 1, 10, 38000.0),
            (2025, 7, 13, -5000.0)
        ) AS t(year, month, hour_local, residual_load);
    """)
    c.execute("""
        CREATE TABLE mart_conditions_hourly AS
        SELECT
            year, month, hour_local, residual_load,
            CASE WHEN month IN (12,1,2) THEN 'winter' WHEN month IN (3,4,5) THEN 'spring'
                 WHEN month IN (6,7,8) THEN 'summer' ELSE 'autumn' END AS season,
            (row_number() OVER (ORDER BY residual_load)) AS residual_decile,
            50.0 + residual_load / 1000.0 AS day_ahead_price,
            (residual_load > 30000) AS net_import_flag,
            (residual_load < 0) AS negative_price_flag,
            greatest(0.0, 1 - residual_load / 50000.0) AS vre_coverage
        FROM fact_hourly;
    """)
    c.execute("""
        CREATE TABLE mart_daily_summary AS
        SELECT year, sum(net_import) AS net_import_mwh,
               bool_or(net_import > 0) AS net_importer_day
        FROM (SELECT year, (residual_load - 30000) * 100 AS net_import FROM fact_hourly)
        GROUP BY year;
    """)
    c.execute("""
        CREATE TABLE fact_forecast_hourly AS
        SELECT year, month, hour_local,
            5000.0 AS actual_load, 300.0 AS error_load,
            2000.0 AS actual_wind, 200.0 AS error_wind,
            1000.0 AS actual_solar, 100.0 AS error_solar,
            2000.0 AS actual_residual, 250.0 AS error_residual
        FROM fact_hourly;
    """)
    return c


ALL_YEARS = list(q.YEARS)
ALL_SEASONS = list(q.SEASONS)


def test_residual_duration_has_endpoints_per_year(con):
    df = q.residual_duration(con, [2019, 2025])
    assert set(df.columns) == {"year", "pct_hours", "residual_load"}
    assert set(df["year"]) == {2019, 2025}


def test_residual_profile_and_metrics(con):
    prof = q.residual_profile_by_hour(con, ALL_YEARS, ALL_SEASONS)
    assert list(prof.columns) == ["hour_local", "avg_residual"]
    m = q.residual_metrics(con, ALL_YEARS, ALL_SEASONS).iloc[0]
    assert m.hours == 4 and m.hours_below_zero == 1


def test_price_by_decile_shape(con):
    df = q.price_by_decile(con, ALL_YEARS, ALL_SEASONS)
    assert "median_price" in df.columns and "avg_vre_coverage" in df.columns
    assert len(df) >= 1


def test_import_functions(con):
    assert list(q.import_by_year(con, ALL_YEARS).columns) == [
        "year", "net_importer_days", "net_import_twh",
    ]
    assert list(q.import_share_by_hour(con, ALL_YEARS, ALL_SEASONS).columns) == [
        "hour_local", "net_importer_pct",
    ]
    bands = q.import_share_by_vre_band(con, ALL_YEARS, ALL_SEASONS)
    assert "vre_band" in bands.columns


def test_forecast_functions(con):
    ov = q.forecast_mae_overall(con, ALL_YEARS, ALL_SEASONS).iloc[0]
    assert ov.mae_load == 300 and ov.load_pct == 6.0  # 300/5000
    assert q.forecast_mae_by_year(con).shape[0] == 2
    assert q.forecast_mae_by_month(con, ALL_YEARS).shape[0] == 2
    assert q.forecast_mae_by_hour(con, ALL_YEARS, ALL_SEASONS).shape[0] == 2


def test_season_filter_reduces_rows(con):
    # winter-only should drop the July (summer) rows
    winter = q.residual_profile_by_hour(con, ALL_YEARS, ["winter"])
    both = q.residual_profile_by_hour(con, ALL_YEARS, ALL_SEASONS)
    assert len(winter) < len(both)


def test_year_filter_bites(con):
    one = q.import_by_year(con, [2025])
    assert set(one["year"]) == {2025}


def test_invalid_season_falls_back_to_all(con):
    # a bogus season list must not crash or inject; it falls back to all seasons
    df = q.residual_profile_by_hour(con, ALL_YEARS, ["'; DROP TABLE fact_hourly; --"])
    assert not df.empty
