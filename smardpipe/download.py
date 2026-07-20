"""Download raw SMARD chart-data weekly JSON files.

Design notes (all from docs/data_dictionary.md):
  * The weekly ``index_*.json`` is a generic 2014->2026 superset and does NOT
    prove coverage, so we still assert coverage later in the build step. Here we
    only use it to enumerate the weekly file timestamps to fetch.
  * Every data file carries ``meta_data.created``. Values can be revised with no
    fixed schedule, so we record ``created`` per file in a manifest.
  * Network access is injected via ``fetch_json`` so the logic is unit-testable
    without hitting the wire. The default uses the stdlib (no ``requests`` dep).
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from . import series as S

FetchJson = Callable[[str], dict]

# A day in ms; weekly index timestamps are week-start instants.
_MS_PER_DAY = 86_400_000


def _http_get_json(url: str, *, retries: int = 3, pause: float = 1.0) -> dict:
    """Minimal stdlib GET returning parsed JSON, with a small retry."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "smardpipe"})
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except Exception as err:  # pragma: no cover - network path
            last_err = err
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url}") from last_err


def index_url(s: S.SmardSeries, resolution: str) -> str:
    return f"{S.CHART_DATA_HOST}/{s.data_id}/{s.region}/index_{resolution}.json"


def data_url(s: S.SmardSeries, resolution: str, week_start: int) -> str:
    stem = f"{s.data_id}_{s.region}_{resolution}_{week_start}"
    return f"{S.CHART_DATA_HOST}/{s.data_id}/{s.region}/{stem}.json"


def raw_filename(s: S.SmardSeries, resolution: str, week_start: int) -> str:
    return f"{s.data_id}_{s.region}_{resolution}_{week_start}.json"


def _to_ms(date_str: str) -> int:
    """UTC midnight epoch-ms for a 'YYYY-MM-DD' string."""
    import datetime as dt

    d = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


def weeks_in_window(
    timestamps: list[int], start: str, end: str
) -> list[int]:
    """Week-start timestamps whose 7-day span overlaps [start, end].

    Keeps the week containing ``start`` (its span may begin a few hours before)
    and every week up to and including the one containing ``end``.
    """
    start_ms = _to_ms(start)
    end_ms = _to_ms(end) + _MS_PER_DAY  # include all of the end day
    out = []
    for ts in sorted(timestamps):
        week_end = ts + 7 * _MS_PER_DAY
        if week_end > start_ms and ts < end_ms:
            out.append(ts)
    return out


def download_series(
    s: S.SmardSeries,
    raw_dir: Path,
    *,
    start: str = S.WINDOW_START,
    end: str = S.WINDOW_END,
    fetch_json: FetchJson = _http_get_json,
    overwrite: bool = False,
) -> list[dict]:
    """Download every in-window weekly file for one series.

    Returns manifest rows (one per week) recording ``created`` and the cached
    path. Files already present are skipped unless ``overwrite`` is set.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    idx = fetch_json(index_url(s, s.resolution))
    weeks = weeks_in_window(idx["timestamps"], start, end)

    rows: list[dict] = []
    for week_start in weeks:
        fname = raw_filename(s, s.resolution, week_start)
        path = raw_dir / fname
        if path.exists() and not overwrite:
            payload = json.loads(path.read_text())
        else:
            payload = fetch_json(data_url(s, s.resolution, week_start))
            path.write_text(json.dumps(payload))
        rows.append(
            {
                "key": s.key,
                "data_id": s.data_id,
                "region": s.region,
                "resolution": s.resolution,
                "week_start": week_start,
                "created": payload.get("meta_data", {}).get("created"),
                "path": str(path),
            }
        )
    return rows


def download_all(
    raw_dir: Path,
    *,
    start: str = S.WINDOW_START,
    end: str = S.WINDOW_END,
    fetch_json: FetchJson = _http_get_json,
    overwrite: bool = False,
) -> list[dict]:
    """Download every registered raw series; return the combined manifest."""
    manifest: list[dict] = []
    for s in S.raw_series():
        manifest.extend(
            download_series(
                s, raw_dir, start=start, end=end,
                fetch_json=fetch_json, overwrite=overwrite,
            )
        )
    return manifest


def write_manifest(rows: list[dict], path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["key", "data_id", "region", "resolution",
              "week_start", "created", "path"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
