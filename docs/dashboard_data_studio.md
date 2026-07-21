# Data Studio dashboard — build guide

The portfolio dashboard is a 3-page Data Studio report with a public link. This
guide is the recipe: which data feeds it, what to put on each page, and how to
publish. It sits on CSV extracts written by `scripts/export_data_studio.py`, so
the whole thing rebuilds from the pipeline.

(Data Studio is Google's free reporting product. Google called it Looker Studio
from 2022 and renamed it back to Data Studio in April 2026; some job ads and help
articles may still say "Looker Studio" during the transition — same tool.
Existing reports and shared links carried over automatically.)

It's a screening / reporting tool, not a trading or dispatch tool — every page
says so, and every headline is observational (an association across 2019–2025),
never causal.

## 1. Generate the data

```bash
python scripts/export_data_studio.py        # writes exports/data_studio/*.csv
```

Six files land in `exports/data_studio/`:

| File | Grain | Feeds | Why it exists |
|---|---|---|---|
| `conditions_hourly.csv` | one row / UTC hour | Pages 1–2 + all filters | Data Studio aggregates and filters this live |
| `forecast_hourly.csv` | one row / UTC hour | Page 3 | `abs_error_*` precomputed so MAE = `AVG(abs_error_x)` |
| `price_by_decile.csv` | 10 rows | Page 1 headline | **median** price per decile — Data Studio has no reliable live median, so it's done in SQL |
| `residual_duration_by_year.csv` | ~200 pts/yr | Page 1 | a duration curve is a per-year sort, which a BI tool can't build from an unordered table |
| `coverage_by_year.csv` | 7 rows | Page 3 data notes | completeness / gap counts |
| `daily_summary.csv` | one row / day | Page 2 headline | net-importer days and TWh per year |

The two precompute choices (median, duration curve) are deliberate: they're the
things Data Studio genuinely can't do over a live source, so they're pinned in
SQL where they're reproducible and testable.

## 2. Connect the data in Data Studio

For each CSV: **Create → Data source → File Upload → upload the CSV**. Simplest,
free, and the resulting report publishes to a public link. (If you'd rather the
report refresh when the data changes, paste each CSV into its own Google Sheet
tab and use the Google Sheets connector instead — same field names, live refresh.)

Check field types after upload: `year`, `month`, `hour_local`, `residual_decile`,
`price_decile` should be **Number** (or Dimension where used as an axis);
`date_local` should be **Date**; `season`, `day_type` are Text dimensions.

Create three calculated fields on `conditions_hourly` (Resource → Manage data
sources → edit fields, or add as chart metrics):

- **Net-import rate** = `AVG(net_importer)` — format as Percent. (`net_importer`
  is 0/1, so its average is the share of hours importing.)
- **Negative-price rate** = `AVG(negative_price)` — format as Percent.
- **VRE band** = `CASE WHEN vre_coverage < 0.2 THEN "<0.2" WHEN vre_coverage < 0.4 THEN "0.2–0.4" WHEN vre_coverage < 0.6 THEN "0.4–0.6" WHEN vre_coverage < 0.8 THEN "0.6–0.8" ELSE "≥0.8" END`

On `forecast_hourly`, the four MAE metrics are just the `abs_error_*` columns with
aggregation **Average**: MAE Load = `AVG(abs_error_load)`, and likewise wind,
solar, residual.

## 3. Page 1 — System Pressure

The headline "when is the system tight" view.

- **Scorecards (top row), source `conditions_hourly`:** Peak residual =
  `MAX(residual_load)`; Avg residual = `AVG(residual_load)`; Hours residual < 0 =
  `COUNT` with a filter `residual_load < 0`.
- **Duration curve, source `residual_duration_by_year`:** Line chart. Dimension
  `pct_hours` (X), Metric `residual_load` (Y, AVG), Breakdown dimension `year`.
  Add a reference line at 0. Title: "Residual-load duration curve by year".
- **Price by pressure, source `price_by_decile`:** Combo/bar chart. Dimension
  `residual_decile`; bars `median_price` and `mean_price` (both AVG — one row per
  decile so the average is the value). Title: "Day-ahead price by residual decile
  (median vs mean)". The mean pulling above the median in decile 10 is the spike
  tail — call it out in the caption.
- **Residual profile, source `conditions_hourly`:** Line chart. Dimension
  `hour_local` (X), Metric `residual_load` (AVG), optional breakdown `season`.

Caption (edit numbers if you refilter): *During 2019–2025, hours in the tightest
residual decile had a median day-ahead price of €110/MWh vs €88 in the middle
decile, and the annual residual trough fell from +2.5 GW (2019) to −8.4 GW (2025).
Observational — it doesn't isolate fuel, carbon, or neighbouring-market effects.*

## 4. Page 2 — Imports & Price Conditions

Net-import rate and price across observable conditions, fully filterable.

- **Filter controls (top of page), source `conditions_hourly`:** drop-down
  controls for `year`, `season`, `day_type`, and `residual_decile` (label it
  "Residual band"). These filter every chart on the page that uses
  `conditions_hourly`.
- **Net-importer days & TWh by year, source `daily_summary`:** Column chart.
  Dimension `year`; metric 1 = net-importer days = `COUNT` filtered to
  `net_importer_day = true` (or `SUM` of a 0/1 field); metric 2 (second axis) =
  `SUM(net_import_mwh)/1e6` as "Net import (TWh)".
- **Net-import rate by hour, source `conditions_hourly`:** Line chart. Dimension
  `hour_local`, Metric **Net-import rate**.
- **Net-import rate by VRE band, source `conditions_hourly`:** Bar chart.
  Dimension **VRE band**, Metric **Net-import rate**.
- **Price distribution by decile, source `conditions_hourly`:** Bar of
  `AVG(day_ahead_price)` by `residual_decile` (this one moves with the filters,
  where the Page-1 median table is fixed). Optionally add **Negative-price rate**.

Caption: *During 2019–2025, Germany was a commercial net importer in ~62% of
tightest-decile hours vs ~8% of loosest-decile hours; net-importer days rose from
99 (2022) to 281 (2024) around the April-2023 nuclear phase-out. This is a
commercial (market-coupled) position, not physical adequacy.*

## 5. Page 3 — Forecast Quality & Data Notes

- **MAE scorecards, source `forecast_hourly`:** MAE Load / Wind / Solar /
  Residual (the four `AVG(abs_error_*)` metrics).
- **MAE by hour, source `forecast_hourly`:** Line chart. Dimension `hour_local`;
  metrics the four MAE fields. Solar's midday bulge should be obvious.
- **MAE by month, source `forecast_hourly`:** Line chart. Dimension `month`;
  same four metrics. Add a `season`/`year` filter control here (fields exist in
  this source).
- **Data notes & completeness, source `coverage_by_year`:** Table. Dimension
  `year`; metrics `hours`, `missing_price_hours`, `missing_residual_hours`,
  `missing_net_import_hours`. The ~52 missing net-import hours (2019–2022) sit at
  the seam between SMARD series 661 and 4629 — note that under the table.
- **Text boxes:** source & attribution — "Bundesnetzagentur | SMARD.de, CC BY
  4.0"; window "2019-01-01 → 2025-12-31, hourly"; the definitions that prevent
  overclaiming: residual load = load − wind − solar; day-ahead price is the DE-LU
  auction, not "the" electricity price; net imports are a commercial position.

Caption: *Day-ahead MAE across 2019–2025: load 3.8%, wind 8.7%, solar 7.3% of
mean actual; residual is 2,548 MW because it compounds the three. Wind is the
relative limiter; residual error peaks at midday. Solar's absolute MAE roughly
doubled with the growing PV fleet, not method drift.*

## 6. Publish the public link

1. **Share → Manage access.**
2. Set link access to **"Anyone on the internet can find and view"** (this is what
   makes it a genuine public portfolio link).
3. Copy the link and paste it into the README's "Live dashboard" line.
4. Optional: **File → Embed report** if you want to embed it anywhere.

## 7. Maintenance ("who runs this every week?")

To refresh after a data rebuild: re-run `python scripts/export_data_studio.py`,
then in each File-Upload data source click **Edit → re-upload** the CSV (or, if
you used Google Sheets, just repaste — the report refreshes on its own). Nothing
in the report layout has to change; the schema is stable. Keep the report on the
same six sources so the public link never changes.
