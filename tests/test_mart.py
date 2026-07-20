"""mart_conditions_hourly SQL transform: derivations, flags, null-safe deciles."""

import duckdb
import pandas as pd

from smardpipe import mart


def _con(df):
    con = duckdb.connect()
    con.register("fh", df)
    con.execute("CREATE TABLE fact_hourly AS SELECT * FROM fh")
    return con


def _fact(n=11):
    ts = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        "hour_ms": range(n),
        "ts_utc": ts,
        "ts_local": ts.tz_localize(None),
        "date_local": [pd.Timestamp("2024-01-01").date()] * n,
        "year": [2024] * n,
        "month": [1] * n,
        "hour_local": list(range(n)),
        "dow": [0] * n,
        "is_weekend": [False] * n,
        "load": [1000.0] * n,
        "wind_onshore": [100.0] * n,
        "wind_offshore": [50.0] * n,
        "solar": [50.0] * n,
        "residual_load": [float(x) for x in range(100, 100 + n * 10, 10)][:n],
        "day_ahead_price": [-5.0] + [float(i) for i in range(1, n)],
        "commercial_net_export": [-200.0] + [200.0] * (n - 1),
        "net_import": [200.0] + [-200.0] * (n - 1),
    })
    df.loc[n - 1, "residual_load"] = None  # one gap -> NULL decile
    return df


def _mart(df):
    con = _con(df)
    mart.build_mart(con)
    m = con.execute(
        "SELECT * FROM mart_conditions_hourly ORDER BY hour_ms"
    ).df()
    con.close()
    return m


def test_derived_columns():
    m = _mart(_fact())
    # vre_generation = 200, coverage = 200/1000
    assert (m["vre_generation"] == 200.0).all()
    assert (m["vre_coverage"].round(3) == 0.2).all()
    assert m["season"].iloc[0] == "winter"


def test_flags():
    m = _mart(_fact())
    assert bool(m.loc[0, "negative_price_flag"]) is True    # price -5
    assert bool(m.loc[1, "negative_price_flag"]) is False
    assert bool(m.loc[0, "net_import_flag"]) is True         # net_import +200
    assert bool(m.loc[1, "net_import_flag"]) is False        # -200


def test_deciles_cover_1_to_10_and_null_is_not_binned():
    m = _mart(_fact())
    # 10 non-null residual rows -> deciles 1..10 exactly once each
    good = m["residual_decile"].dropna().astype(int)
    assert sorted(good) == list(range(1, 11))
    # the gap row has NULL residual_load -> NULL decile (not decile 1)
    assert pd.isna(m.loc[10, "residual_decile"])


def test_daily_summary_rollup():
    n = 11
    con = _con(_fact(n))
    mart.build_mart(con)
    mart.build_daily(con)
    d = con.execute("SELECT * FROM mart_daily_summary").df()
    con.close()

    assert len(d) == 1  # all rows share one date
    row = d.iloc[0]
    assert row["n_hours"] == n
    assert row["load_mwh"] == 11000.0            # 11 * 1000, summed
    assert row["vre_generation_mwh"] == 2200.0   # 11 * 200
    assert round(row["vre_coverage"], 3) == 0.2
    # price averaged: mean of [-5, 1..10] = (-5 + 55) / 11
    assert round(row["avg_price"], 3) == round((-5 + 55) / 11, 3)
    assert row["negative_price_hours"] == 1
    # net_import = +200 once, -200 ten times -> -1800 total, not an import day
    assert row["net_import_mwh"] == -1800.0
    assert row["net_import_hours"] == 1
    assert bool(row["net_importer_day"]) is False
