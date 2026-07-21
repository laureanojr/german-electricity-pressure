# German Electricity: Demand, Supply Pressure & Price

Using seven years of public German electricity data (SMARD, 2019–2025), this project
shows when the system comes under pressure — when demand outruns cheap renewable supply,
when the country leans on imports, and when wholesale prices spike — and measures how far
ahead you can see it coming from day-ahead forecasts. It is a screening / reporting tool,
not a trading or dispatch tool.

**Status:** Step 1 (data foundation). The download → `fact_hourly` pipeline is built and
tested; the four analyses and dashboard come later.

## Data source

[SMARD](https://www.smard.de) (Bundesnetzagentur), CC BY 4.0 — attribute as
"Bundesnetzagentur | SMARD.de". Series names, IDs, units, timezone and revision behaviour
are documented in [`docs/data_dictionary.md`](docs/data_dictionary.md); open questions and
modelling decisions in [`docs/methodology.md`](docs/methodology.md). Every factual claim in
those docs is traceable to an official SMARD source.

## Reproduce Step 1

Requires Python 3.12 and the pinned deps.

```bash
pip install -r requirements.txt

# 1. Download raw weekly JSON into data/raw (live; hits smard.de). Cached +
#    resumable; records each file's meta_data.created in data/raw/manifest.csv.
python scripts/download_smard.py                 # full 2019–2025 window
# (or a slice while iterating: --start 2024-01-01 --end 2024-12-31)

# 2. Build fact_hourly: aggregate 15-min → hour, compute residual, stitch the
#    commercial net-export series, assert coverage, write parquet + DuckDB.
python scripts/build_fact_hourly.py

# 3. Build fact_forecast_hourly: day-ahead forecast vs actual for
#    load / wind / solar / residual, with error columns.
python scripts/build_forecast_hourly.py

# 4. Build the marts: mart_conditions_hourly (the dashboard base) and
#    mart_daily_summary (per-day rollup).
python scripts/build_mart.py

# 5. Sanity check: reconcile completed-2025 totals against official
#    Bundesnetzagentur figures (fails loudly if any drifts).
python scripts/reconcile_2025.py
```

**Tables** (in `data/processed/gep.duckdb` + Parquet): `fact_hourly` and
`fact_forecast_hourly` (one row per UTC hour), `mart_conditions_hourly` (hourly,
adds residual/price deciles, VRE coverage, net-import & negative-price flags —
the dashboard base), and `mart_daily_summary` (one row per Berlin day).

The 2025 reconciliation passes on all four metrics — net generation 437.90 vs
437.6 TWh, day-ahead price €89.32 (exact), net imports 21.92 vs 21.9 TWh, and 573
negative-price hours (exact). It runs in CI as a real gate: because `data/` is
gitignored, `tests/test_reconcile_real_2025.py` reconciles a committed ~350 KB
slice of the actual 2025 data (`tests/fixtures/fact_2025_reconcile.parquet`)
against the official figures on every push. Regenerate that fixture with
`python scripts/reconcile_2025.py --emit-fixture tests/fixtures/fact_2025_reconcile.parquet`.
Details and the pinned "net generation" definition are in
[`docs/methodology.md`](docs/methodology.md).

Outputs: `data/processed/fact_hourly.parquet` and table `fact_hourly` in
`data/processed/gep.duckdb`. The build **fails loudly** if a required series has a
structural coverage gap over the window.

## What `fact_hourly` guarantees

One row per UTC hour, and you can trust the units:

- energy columns (load, generation fuels) are **MWh**, aggregated 15-min → hour by **sum**;
  a missing sub-interval makes the whole hour a gap (no partial sums).
- `day_ahead_price` is **EUR/MWh**, aggregated by **mean**.
- `residual_load` = load − wind onshore − wind offshore − solar (wind + solar only).
- `commercial_net_export` (+ export / − import) is stitched from SMARD filter **661**
  (2019 → 2020-12-31) and **4629** (2021 → present) — same concept, "Kommerzieller
  Nettoexport"; `net_import` = −that. Physical flow is deliberately excluded.
- timestamps are UTC instants; Berlin-local calendar attributes are derived and DST-aware
  (23-/25-hour days handled).

## Layout

```
smardpipe/        pipeline package (series, download, transform, build, forecast, reconcile, mart)
scripts/          thin CLIs: download_smard, build_fact_hourly, build_forecast_hourly, build_mart, reconcile_2025
sql/              mart_conditions_hourly.sql, mart_daily_summary.sql (DuckDB transforms)
tests/            fixture-based unit tests (units, DST, gaps, stitch, coverage, forecast, reconcile, marts)
docs/             data_dictionary.md, methodology.md
data/             raw/ and processed/ (gitignored)
```

## Tests

```bash
ruff check .
pytest -q
```

CI runs both on every push. Tests use fixtures (no network), including the with-teeth
check that an hour equals the **sum** of its four quarter-hours, that DST days carry 23/25
hours, that the coverage assertion actually fails on a structural gap, and that the real
2025 aggregates still reconcile against the official Bundesnetzagentur figures.
