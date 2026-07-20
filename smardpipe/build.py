"""Assemble ``fact_hourly`` from processed series and assert coverage.

Output contract ("you can query any hour and trust the units"):
  * one row per UTC hour across the project window;
  * energy columns in MWh (summed), price in EUR/MWh (mean);
  * residual_load computed as load - wind_onshore - wind_offshore - solar;
  * commercial_net_export stitched (661 -> 4629), net_import = -that;
  * DST-aware calendar attributes derived from the UTC instant.

Coverage is asserted, not assumed: the frame is reindexed onto a complete
hourly grid so missing hours are explicit, then required columns must clear a
completeness floor and a max-gap ceiling (this is what catches things like the
cross-border series being absent for a period).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from . import series as S
from . import transform as T

_MS_PER_HOUR = 3_600_000
_BERLIN = ZoneInfo("Europe/Berlin")

# Columns whose coverage is load-bearing for the four analyses.
REQUIRED_COLUMNS = (
    "load", "wind_onshore", "wind_offshore", "solar",
    "lignite", "hard_coal", "gas",
    "day_ahead_price", "commercial_net_export",
)


def _local_hour_ms(date_str: str, hour: int) -> int:
    """Epoch-ms of a Berlin wall-clock hour (DST-correct)."""
    ts = pd.Timestamp(f"{date_str} {hour:02d}:00", tz=_BERLIN)
    return int(ts.tz_convert("UTC").value // 1_000_000)


def expected_hour_index(
    start: str = S.WINDOW_START, end: str = S.WINDOW_END
) -> pd.Index:
    """Complete hourly grid (epoch ms) covering the Berlin-local window.

    Built in epoch space, so DST days naturally carry 23/25 hourly buckets once
    the hours are grouped back into Berlin calendar days.
    """
    start_ms = _local_hour_ms(start, 0)
    end_ms = _local_hour_ms(end, 23)  # last local hour of the end day
    return pd.RangeIndex(start_ms, end_ms + _MS_PER_HOUR, _MS_PER_HOUR)


def build_fact_hourly(
    raw_dir: Path, *, start: str = S.WINDOW_START, end: str = S.WINDOW_END
) -> pd.DataFrame:
    """Build the wide fact table from cached raw files."""
    cols: dict[str, pd.Series] = {}
    for s in [S.LOAD, *S.GENERATION]:
        cols[s.key] = T.series_hourly(raw_dir, s)
    cols[S.PRICE.key] = T.series_hourly(raw_dir, S.PRICE)
    cols[S.RESIDUAL_SMARD.key] = T.series_hourly(raw_dir, S.RESIDUAL_SMARD)

    old = T.series_hourly(raw_dir, S.COMMERCIAL_NETEXPORT_OLD)
    new = T.series_hourly(raw_dir, S.COMMERCIAL_NETEXPORT_NEW)
    cols["commercial_net_export"] = T.stitch_commercial_net_export(old, new)

    wide = pd.DataFrame(cols)
    wide = wide.reindex(expected_hour_index(start, end))
    wide.index.name = "hour_ms"

    wide = T.add_residual_load(wide)
    wide["net_import"] = -wide["commercial_net_export"]

    return _add_calendar(wide).reset_index()


def _add_calendar(wide: pd.DataFrame) -> pd.DataFrame:
    utc = pd.to_datetime(wide.index, unit="ms", utc=True)
    local = utc.tz_convert(_BERLIN)
    wide = wide.copy()
    wide["ts_utc"] = utc
    wide["ts_local"] = local.tz_localize(None)
    wide["date_local"] = local.date
    wide["year"] = local.year
    wide["month"] = local.month
    wide["hour_local"] = local.hour
    wide["dow"] = local.dayofweek  # Mon=0
    wide["is_weekend"] = local.dayofweek >= 5
    return wide


# --- Coverage ---------------------------------------------------------------
@dataclass(frozen=True)
class CoverageThresholds:
    min_completeness: float = 0.98
    max_gap_hours: int = 48


def coverage_report(
    fact: pd.DataFrame, columns=REQUIRED_COLUMNS
) -> pd.DataFrame:
    """Per-column completeness and worst consecutive gap over the grid."""
    n = len(fact)
    rows = []
    for col in columns:
        present = fact[col].notna()
        n_present = int(present.sum())
        # longest run of consecutive missing hours
        missing = (~present).astype(int)
        grp = (present).cumsum()
        max_gap = int(missing.groupby(grp).sum().max()) if n else 0
        first = fact.loc[present, "ts_utc"].min() if n_present else pd.NaT
        last = fact.loc[present, "ts_utc"].max() if n_present else pd.NaT
        rows.append({
            "column": col,
            "n_hours": n,
            "n_present": n_present,
            "completeness": (n_present / n) if n else 0.0,
            "max_gap_hours": max_gap,
            "first_present": first,
            "last_present": last,
        })
    return pd.DataFrame(rows)


def assert_coverage(
    fact: pd.DataFrame,
    columns=REQUIRED_COLUMNS,
    thresholds: CoverageThresholds = CoverageThresholds(),
) -> pd.DataFrame:
    """Raise if any required column fails completeness or max-gap. Returns the
    coverage report on success so callers can log/print it."""
    report = coverage_report(fact, columns)
    problems = report[
        (report["completeness"] < thresholds.min_completeness)
        | (report["max_gap_hours"] > thresholds.max_gap_hours)
    ]
    if not problems.empty:
        lines = [
            f"  {r.column}: completeness={r.completeness:.4f}, "
            f"max_gap_hours={r.max_gap_hours}"
            for r in problems.itertuples()
        ]
        raise AssertionError(
            "fact_hourly coverage check failed for:\n" + "\n".join(lines)
        )
    return report


# --- Output -----------------------------------------------------------------
def write_outputs(
    fact: pd.DataFrame, processed_dir: Path, duckdb_path: Path
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = processed_dir / "fact_hourly.parquet"
    fact.to_parquet(parquet_path, index=False)

    import duckdb

    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute(
            "CREATE OR REPLACE TABLE fact_hourly AS "
            "SELECT * FROM read_parquet(?)",
            [str(parquet_path)],
        )
    finally:
        con.close()
