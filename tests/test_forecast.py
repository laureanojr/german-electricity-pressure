"""fact_forecast_hourly: forecast/actual alignment, wind sum, residual, errors."""

import json

from smardpipe import forecast
from smardpipe import series as S

Q = 900_000


def _dump(raw_dir, s, ts, pts):
    name = f"{s.data_id}_{s.region}_{s.resolution}_{ts}.json"
    (raw_dir / name).write_text(
        json.dumps({"meta_data": {"created": 0}, "series": pts})
    )


def _gen(key):
    return next(s for s in S.GENERATION if s.key == key)


def _write(raw_dir, start, end):
    from smardpipe import build

    grid = list(build.expected_hour_index(start, end))

    def quarters(v):
        return [[h + i * Q, v] for h in grid for i in range(4)]

    # actuals (quarter values -> hourly sums: load 4000, won 400, woff 200, sol 100)
    _dump(raw_dir, S.LOAD, grid[0], quarters(1000.0))
    _dump(raw_dir, _gen("wind_onshore"), grid[0], quarters(100.0))
    _dump(raw_dir, _gen("wind_offshore"), grid[0], quarters(50.0))
    _dump(raw_dir, _gen("solar"), grid[0], quarters(25.0))
    # forecasts (hourly: load 3600, won 360, woff 160, sol 80)
    _dump(raw_dir, S.FORECAST_LOAD, grid[0], quarters(900.0))
    _dump(raw_dir, S.FORECAST_WIND_ONSHORE, grid[0], quarters(90.0))
    _dump(raw_dir, S.FORECAST_WIND_OFFSHORE, grid[0], quarters(40.0))
    _dump(raw_dir, S.FORECAST_SOLAR, grid[0], quarters(20.0))


def test_forecast_table_values(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    start, end = "2024-06-01", "2024-06-03"
    _write(raw, start, end)

    fact = forecast.build_forecast_hourly(raw, start=start, end=end)

    assert (fact["actual_load"] == 4000.0).all()
    assert (fact["forecast_load"] == 3600.0).all()
    # wind = onshore + offshore, on both sides
    assert (fact["actual_wind"] == 600.0).all()
    assert (fact["forecast_wind"] == 520.0).all()
    # residual derived identically on both sides
    assert (fact["actual_residual"] == 3300.0).all()     # 4000-600-100
    assert (fact["forecast_residual"] == 3000.0).all()   # 3600-520-80
    # error = forecast - actual
    assert (fact["error_load"] == -400.0).all()
    assert (fact["error_wind"] == -80.0).all()
    assert (fact["error_solar"] == -20.0).all()
    assert (fact["error_residual"] == -300.0).all()

    forecast.assert_coverage(fact)  # must not raise


def test_forecast_coverage_fails_when_forecast_absent(tmp_path):
    import pytest

    raw = tmp_path / "raw"
    raw.mkdir()
    start, end = "2024-06-01", "2024-06-03"
    _write(raw, start, end)
    for f in raw.glob("411_*.json"):  # drop forecast load
        f.unlink()

    fact = forecast.build_forecast_hourly(raw, start=start, end=end)
    with pytest.raises(AssertionError, match="forecast_load"):
        forecast.assert_coverage(fact)
