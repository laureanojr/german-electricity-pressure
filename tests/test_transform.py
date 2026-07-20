"""Transform tests: the units discipline, gap propagation, stitch, residual."""

import numpy as np
import pandas as pd

from smardpipe import series as S
from smardpipe import transform as T

HOUR = 3_600_000
Q = 900_000
# Real SMARD load values for the hour beginning 2019-07-01 00:00 local.
TS0 = 1561932000000
REAL_QUARTERS = [11723.25, 11564.5, 11444.75, 11297.0]
REAL_HOUR_SUM = 46029.5  # SMARD's own hourly value for that hour


def _qh_frame(values, ts0=TS0):
    ts = [ts0 + i * Q for i in range(len(values))]
    return pd.DataFrame({"ts": ts, "value": values})


def test_energy_hour_is_sum_of_quarters_and_matches_native():
    df = _qh_frame(REAL_QUARTERS)
    out = T.aggregate_to_hour(df, kind="energy", resolution="quarterhour")
    assert out.loc[TS0] == REAL_HOUR_SUM  # sum, not mean (mean would be ~11507)
    assert abs(out.loc[TS0] - sum(REAL_QUARTERS)) < 1e-9


def test_price_aggregates_by_mean():
    df = _qh_frame([10.0, 20.0, 30.0, 40.0])
    out = T.aggregate_to_hour(df, kind="price", resolution="quarterhour")
    assert out.loc[TS0] == 25.0  # mean, never sum


def test_missing_subinterval_makes_hour_a_gap():
    df = _qh_frame([11723.25, None, 11444.75, 11297.0])
    out = T.aggregate_to_hour(df, kind="energy", resolution="quarterhour")
    assert np.isnan(out.loc[TS0])


def test_short_hour_is_a_gap():
    df = _qh_frame([1.0, 2.0, 3.0])  # only three quarters present
    out = T.aggregate_to_hour(df, kind="energy", resolution="quarterhour")
    assert np.isnan(out.loc[TS0])


def test_hour_native_passthrough():
    df = pd.DataFrame({"ts": [TS0, TS0 + HOUR], "value": [50.0, 60.0]})
    out = T.aggregate_to_hour(df, kind="price", resolution="hour")
    assert out.loc[TS0] == 50.0
    assert out.loc[TS0 + HOUR] == 60.0


def _boundary_ms():
    import datetime as dt

    b = dt.datetime.strptime(
        S.COMMERCIAL_STITCH_BOUNDARY, "%Y-%m-%d"
    ).replace(tzinfo=dt.timezone.utc)
    return int(b.timestamp() * 1000)


def test_commercial_stitch_uses_old_before_new_after():
    b = _boundary_ms()
    old = pd.Series({b - 2 * HOUR: 10.0, b - HOUR: 11.0})
    new = pd.Series({b - HOUR: 99.0, b: 20.0, b + HOUR: 21.0})
    out = T.stitch_commercial_net_export(old, new)
    assert out.loc[b - 2 * HOUR] == 10.0
    assert out.loc[b - HOUR] == 11.0  # old wins in the overlap, not 99
    assert out.loc[b] == 20.0
    assert out.loc[b + HOUR] == 21.0


def test_residual_definition_and_nan_propagation():
    wide = pd.DataFrame(
        {
            "load": [100.0, 100.0],
            "wind_onshore": [10.0, 10.0],
            "wind_offshore": [5.0, 5.0],
            "solar": [20.0, np.nan],
            "hydro": [7.0, 7.0],  # must NOT enter residual
        }
    )
    out = T.add_residual_load(wide)
    assert out["residual_load"].iloc[0] == 65.0  # 100 - 10 - 5 - 20
    assert np.isnan(out["residual_load"].iloc[1])  # NaN solar propagates
