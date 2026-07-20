"""Assemble ``fact_forecast_hourly``: day-ahead forecast vs actual.

One row per UTC hour with the day-ahead forecast and the realised actual for
load, wind (onshore + offshore), solar, and residual load, plus signed error
columns (error = forecast - actual; positive = over-forecast).

Residual is derived on both sides with the *same* formula
(load - wind - solar), so the residual forecast error is apples-to-apples with
the realised residual used elsewhere. Forecasts are the day-ahead series
(411 / 123 / 3791 / 125), confirmed [CFG]; see docs/data_dictionary.md.

MAE and other summaries are left to the analysis layer — this table just holds
the aligned forecast/actual/error columns.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import build
from . import series as S
from . import transform as T

MEASURES = ("load", "wind", "solar", "residual")

REQUIRED_COLUMNS = (
    "forecast_load", "actual_load",
    "forecast_wind", "actual_wind",
    "forecast_solar", "actual_solar",
    "forecast_residual", "actual_residual",
)


def _gen(key: str) -> S.SmardSeries:
    return next(s for s in S.GENERATION if s.key == key)


def build_forecast_hourly(
    raw_dir: Path, *, start: str = S.WINDOW_START, end: str = S.WINDOW_END
) -> pd.DataFrame:
    """Build the forecast-vs-actual table from cached raw files."""
    comp = pd.DataFrame({
        "forecast_load": T.series_hourly(raw_dir, S.FORECAST_LOAD),
        "actual_load": T.series_hourly(raw_dir, S.LOAD),
        "fc_won": T.series_hourly(raw_dir, S.FORECAST_WIND_ONSHORE),
        "fc_woff": T.series_hourly(raw_dir, S.FORECAST_WIND_OFFSHORE),
        "a_won": T.series_hourly(raw_dir, _gen("wind_onshore")),
        "a_woff": T.series_hourly(raw_dir, _gen("wind_offshore")),
        "forecast_solar": T.series_hourly(raw_dir, S.FORECAST_SOLAR),
        "actual_solar": T.series_hourly(raw_dir, _gen("solar")),
    })
    comp = comp.reindex(build.expected_hour_index(start, end))

    out = pd.DataFrame(index=comp.index)
    out.index.name = "hour_ms"
    out["forecast_load"] = comp["forecast_load"]
    out["actual_load"] = comp["actual_load"]
    # NaN in any component propagates (gap-safe).
    out["forecast_wind"] = comp["fc_won"] + comp["fc_woff"]
    out["actual_wind"] = comp["a_won"] + comp["a_woff"]
    out["forecast_solar"] = comp["forecast_solar"]
    out["actual_solar"] = comp["actual_solar"]
    out["forecast_residual"] = (
        out["forecast_load"] - out["forecast_wind"] - out["forecast_solar"]
    )
    out["actual_residual"] = (
        out["actual_load"] - out["actual_wind"] - out["actual_solar"]
    )
    for m in MEASURES:
        out[f"error_{m}"] = out[f"forecast_{m}"] - out[f"actual_{m}"]

    return build._add_calendar(out).reset_index()


def assert_coverage(fact: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Coverage gate for the forecast table's required columns."""
    return build.assert_coverage(fact, columns=REQUIRED_COLUMNS, **kwargs)


def write_outputs(
    fact: pd.DataFrame, processed_dir: Path, duckdb_path: Path
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = processed_dir / "fact_forecast_hourly.parquet"
    fact.to_parquet(parquet_path, index=False)

    import duckdb

    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute(
            "CREATE OR REPLACE TABLE fact_forecast_hourly AS "
            "SELECT * FROM read_parquet(?)",
            [str(parquet_path)],
        )
    finally:
        con.close()
