"""Build tests: DST day lengths, coverage assertion, and an end-to-end build."""

import json

import numpy as np
import pandas as pd
import pytest

from smardpipe import build
from smardpipe import series as S

HOUR = 3_600_000
Q = 900_000


# --- DST day lengths (the 92/96/100 quarter-hour discipline) ----------------
def _day_sizes(start, end):
    idx = build.expected_hour_index(start, end)
    local = pd.to_datetime(idx, unit="ms", utc=True).tz_convert("Europe/Berlin")
    return pd.Series(1, index=local.date).groupby(level=0).size()


def test_spring_forward_day_has_23_hours():
    sizes = _day_sizes("2021-03-28", "2021-03-28")
    assert int(sizes.iloc[0]) == 23


def test_fall_back_day_has_25_hours():
    sizes = _day_sizes("2021-10-31", "2021-10-31")
    assert int(sizes.iloc[0]) == 25


def test_normal_day_has_24_hours():
    sizes = _day_sizes("2021-06-15", "2021-06-15")
    assert int(sizes.iloc[0]) == 24


# --- Coverage assertion has teeth -------------------------------------------
def _min_fact(n=200):
    idx = pd.RangeIndex(0, n * HOUR, HOUR)
    utc = pd.to_datetime(idx, unit="ms", utc=True)
    data = {c: np.ones(n) for c in build.REQUIRED_COLUMNS}
    df = pd.DataFrame(data)
    df["ts_utc"] = utc
    return df


def test_assert_coverage_passes_when_full():
    report = build.assert_coverage(_min_fact())
    assert (report["completeness"] == 1.0).all()


def test_assert_coverage_raises_on_structural_gap():
    fact = _min_fact()
    fact.loc[10:120, "load"] = np.nan  # ~110h hole > max_gap_hours
    with pytest.raises(AssertionError, match="load"):
        build.assert_coverage(fact)


# --- End-to-end build over a small window (incl. a DST day) -----------------
def _write_synthetic_raw(raw_dir, start, end):
    grid = list(build.expected_hour_index(start, end))
    values = {
        "load": 1000.0, "wind_onshore": 100.0, "wind_offshore": 50.0,
        "solar": 25.0, "lignite": 200.0, "hard_coal": 150.0, "gas": 120.0,
        "biomass": 40.0, "hydro": 30.0, "nuclear": 0.0,
        "pumped_storage_gen": 10.0, "other_conventional": 5.0,
        "other_renewable": 8.0, "residual_load_smard": 800.0,
    }
    for s in [S.LOAD, *S.GENERATION, S.RESIDUAL_SMARD]:
        v = values[s.key]
        pts = [[h + i * Q, v] for h in grid for i in range(4)]
        _dump(raw_dir, s, grid[0], pts)
    # price (hour-native) and commercial old/new (hour-native)
    _dump(raw_dir, S.PRICE, grid[0], [[h, 42.0] for h in grid])
    _dump(raw_dir, S.COMMERCIAL_NETEXPORT_OLD, grid[0],
          [[h, None] for h in grid])          # 661 null in 2024 (realistic)
    _dump(raw_dir, S.COMMERCIAL_NETEXPORT_NEW, grid[0],
          [[h, 500.0] for h in grid])         # 4629 carries the window


def _dump(raw_dir, s, ts, pts):
    name = f"{s.data_id}_{s.region}_{s.resolution}_{ts}.json"
    (raw_dir / name).write_text(
        json.dumps({"meta_data": {"created": 0}, "series": pts})
    )


def test_end_to_end_build(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    start, end = "2024-03-25", "2024-03-31"  # includes spring-forward 03-31
    _write_synthetic_raw(raw, start, end)

    fact = build.build_fact_hourly(raw, start=start, end=end)

    # units: hourly load is the SUM of four 1000-MWh quarters
    assert (fact["load"] == 4000.0).all()
    # residual = load - wind_on - wind_off - solar = 4000-400-200-100
    assert (fact["residual_load"] == 3300.0).all()
    # net_import mirrors commercial net export (stitched to 4629 = 500)
    assert (fact["net_import"] == -500.0).all()
    # DST: the 03-31 Berlin day has 23 hourly rows
    day = fact[fact["date_local"].astype(str) == "2024-03-31"]
    assert len(day) == 23

    build.assert_coverage(fact)  # must not raise

    # DuckDB round-trip: table exists and row count matches
    import duckdb

    ddb = tmp_path / "gep.duckdb"
    build.write_outputs(fact, tmp_path / "processed", ddb)
    con = duckdb.connect(str(ddb))
    try:
        n = con.execute("SELECT count(*) FROM fact_hourly").fetchone()[0]
    finally:
        con.close()
    assert n == len(fact)


def test_absent_context_series_does_not_break_build(tmp_path):
    # Reproduces the real June-2024 case: nuclear (phased out 2023) and the
    # retired 661 have no files. Build must still succeed.
    raw = tmp_path / "raw"
    raw.mkdir()
    start, end = "2024-06-01", "2024-06-07"
    _write_synthetic_raw(raw, start, end)
    for f in list(raw.glob("1224_*.json")) + list(raw.glob("661_*.json")):
        f.unlink()

    fact = build.build_fact_hourly(raw, start=start, end=end)
    assert fact["nuclear"].isna().all()              # absent -> all gap
    assert (fact["commercial_net_export"] == 500.0).all()  # 4629 only
    build.assert_coverage(fact)  # nuclear is not required -> still passes


def test_absent_required_series_fails_coverage(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    start, end = "2024-06-01", "2024-06-07"
    _write_synthetic_raw(raw, start, end)
    for f in raw.glob("410_*.json"):  # drop load (required)
        f.unlink()

    fact = build.build_fact_hourly(raw, start=start, end=end)
    with pytest.raises(AssertionError, match="load"):
        build.assert_coverage(fact)
