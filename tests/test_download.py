"""Download tests: window filtering, caching, manifest, injected fetch."""

import json

from smardpipe import download
from smardpipe import series as S

DAY = 86_400_000


def test_weeks_in_window_overlap():
    # Three weekly starts: one fully before, one inside, one at the edge.
    inside = download._to_ms("2020-06-15")
    before = inside - 40 * DAY
    after = inside + 40 * DAY
    weeks = download.weeks_in_window(
        [before, inside, after], "2020-06-10", "2020-06-20"
    )
    assert inside in weeks
    assert before not in weeks  # its 7-day span ends before the window
    assert after not in weeks


def _fake_fetch(index_ts):
    """Return a fetch_json that serves an index then per-week payloads."""
    def fetch(url):
        if "index_" in url:
            return {"timestamps": index_ts}
        # data url ends with _<ts>.json
        ts = int(url.rsplit("_", 1)[1].split(".")[0])
        return {
            "meta_data": {"created": 111 + ts % 7},
            "series": [[ts, 1.0], [ts + 3_600_000, 2.0]],
        }
    return fetch


def test_download_series_caches_and_records_created(tmp_path):
    inside = download._to_ms("2020-06-15")
    s = S.LOAD
    rows = download.download_series(
        s, tmp_path, start="2020-06-10", end="2020-06-20",
        fetch_json=_fake_fetch([inside]),
    )
    assert len(rows) == 1
    assert rows[0]["created"] == 111 + inside % 7
    cached = tmp_path / download.raw_filename(s, s.resolution, inside)
    assert cached.exists()

    # Second call: serve the index, but explode on any DATA fetch. This proves
    # cached data files are reused (the index is always re-read to list weeks).
    def index_only(url):
        if "index_" in url:
            return {"timestamps": [inside]}
        raise AssertionError("should not fetch data; file is cached")

    rows2 = download.download_series(
        s, tmp_path, start="2020-06-10", end="2020-06-20",
        fetch_json=index_only,
    )
    assert json.loads(cached.read_text())["series"][0][1] == 1.0
    assert rows2[0]["path"] == rows[0]["path"]
