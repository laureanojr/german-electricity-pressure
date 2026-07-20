"""Parse, aggregate, and derive hourly series from raw SMARD JSON.

Aggregation rules (official, docs/data_dictionary.md):
  * energy (MWh): hour = SUM of its four quarter-hours.
  * price (EUR/MWh): hour = MEAN.
  * gap propagation: a missing/NaN sub-interval makes the whole hour a gap.

Why epoch-hour bucketing is correct for DST: SMARD timestamps are absolute
instants and Berlin local-hour boundaries fall on UTC hour boundaries (the
offset is a whole number of hours). So every real hour bucket holds exactly
four quarter-hours; the 23-/25-hour "days" only appear when hours are grouped
into Berlin *calendar days* (done at analysis time, not here).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import series as S

_MS_PER_HOUR = 3_600_000
_QUARTERS_PER_HOUR = 4


def parse_payload(payload: dict) -> pd.DataFrame:
    """Raw chart-data JSON -> DataFrame[ts:int64, value:float] (NaN for null)."""
    rows = payload.get("series", [])
    df = pd.DataFrame(rows, columns=["ts", "value"])
    df["ts"] = df["ts"].astype("int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def _read_all_weeks(raw_dir: Path, s: S.SmardSeries) -> pd.DataFrame:
    """Concatenate every cached weekly file for one series, deduped on ts."""
    pattern = f"{s.data_id}_{s.region}_{s.resolution}_*.json"
    frames = [parse_payload(json.loads(p.read_text()))
              for p in sorted(raw_dir.glob(pattern))]
    if not frames:
        raise FileNotFoundError(
            f"No raw files for {s.key} ({pattern}) in {raw_dir}"
        )
    df = pd.concat(frames, ignore_index=True)
    # Adjacent weekly files can repeat a boundary instant; keep the last.
    df = df.drop_duplicates(subset="ts", keep="last").sort_values("ts")
    return df.reset_index(drop=True)


def aggregate_to_hour(df: pd.DataFrame, kind: str, resolution: str) -> pd.Series:
    """Aggregate a [ts, value] frame to an hourly Series indexed by hour-start.

    Energy -> sum, price -> mean. For quarter-hour input, an hour is emitted
    only if all four quarters are present and non-NaN; otherwise it is a gap
    (NaN). Hour-native input is passed through (floored to the hour).
    """
    hour = (df["ts"] // _MS_PER_HOUR) * _MS_PER_HOUR
    work = pd.DataFrame({"hour": hour, "value": df["value"]})

    present = work.groupby("hour")["value"].agg(
        n="size", n_valid="count",
        total="sum", mean="mean",
    )

    if resolution == "quarterhour":
        complete = (present["n"] == _QUARTERS_PER_HOUR) & \
                   (present["n_valid"] == _QUARTERS_PER_HOUR)
    else:  # hour-native: one observation per hour, must be non-null
        complete = present["n_valid"] == present["n"]

    value = present["total"] if kind == "energy" else present["mean"]
    out = value.where(complete)
    out.index.name = "hour"
    out.name = "value"
    return out


def series_hourly(raw_dir: Path, s: S.SmardSeries) -> pd.Series:
    """Fully processed hourly Series for one registered series.

    If the series has no raw files for the requested period (e.g. nuclear after
    the 2023 phase-out, or the retired commercial series 661 in recent years),
    return an empty Series. The column then reindexes to all-gap, and the
    coverage check (which only polices required series) decides if that matters.
    """
    try:
        df = _read_all_weeks(raw_dir, s)
    except FileNotFoundError:
        return pd.Series(dtype="float64", name="value")
    return aggregate_to_hour(df, s.kind, s.resolution)


def stitch_commercial_net_export(
    old: pd.Series, new: pd.Series, boundary: str = S.COMMERCIAL_STITCH_BOUNDARY
) -> pd.Series:
    """Commercial net export across the 661 -> 4629 changeover.

    Uses ``old`` (661) strictly before the boundary instant and ``new`` (4629)
    on/after it. Both are the same concept ("Kommerzieller Nettoexport"); the
    overlap around the boundary is what lets the join be validated elsewhere.
    """
    import datetime as dt

    b = dt.datetime.strptime(boundary, "%Y-%m-%d").replace(
        tzinfo=dt.timezone.utc)
    b_ms = int(b.timestamp() * 1000)

    old_part = old[old.index < b_ms]
    new_part = new[new.index >= b_ms]
    out = pd.concat([old_part, new_part])
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.name = "commercial_net_export"
    return out


def add_residual_load(wide: pd.DataFrame) -> pd.DataFrame:
    """residual_load = load - wind_onshore - wind_offshore - solar (NaN-safe).

    Definition lives in one place (series.VRE_FOR_RESIDUAL). NaN in any input
    propagates, so a residual value only exists where all inputs exist.
    """
    cols = [S.LOAD.key, *S.VRE_FOR_RESIDUAL]
    missing = [c for c in cols if c not in wide.columns]
    if missing:
        raise KeyError(f"residual inputs missing from fact table: {missing}")
    vre = wide[list(S.VRE_FOR_RESIDUAL)].sum(axis=1, skipna=False)
    wide = wide.copy()
    wide["residual_load"] = wide[S.LOAD.key] - vre
    return wide
