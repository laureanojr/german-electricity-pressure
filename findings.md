# Findings — German electricity: demand, supply pressure & price (2019–2025)

Over 2019–2025 the German system moved from a comfortable net exporter with a
flat daytime demand plateau to one whose stress sits in low-VRE evenings and
whose cheapest hours are defined by surplus wind and solar. The four findings
below back that up: the residual-load duration curve is pivoting rather than
shifting, price and its spike risk climb together with supply pressure, the
commercial trade position flipped to net importer in 2023, and day-ahead
forecasts still call next-day pressure within a few percent.

Every number here is produced by SQL in `sql/findings/` and printed by
`python scripts/run_findings.py`; nothing is hand-typed. Each finding cites the
query block (`file.sql: block_name`) behind it. Relationships aren't stationary
across the window — nuclear went to ~0 in April 2023 and the PV fleet kept
growing — so anything that can move is reported by year. Residual load is
`load − wind_onshore − wind_offshore − solar` throughout (wind + solar only);
that's a modelling choice, not SMARD's own Residuallast. Findings are stated
observationally: an association in the data, not a cause.

---

## 1. Residual load: the duration curve is pivoting, not sliding

**Headline.** The annual residual peak barely moved (about 75 GW in 2019 to 68
GW in 2025), but the bottom of the curve fell through zero — the annual trough
went from +2.5 GW in 2019 to −8.4 GW in 2025, and 2025 had 202 hours where wind
and solar alone out-produced load, against none before 2023. **Decision it
supports:** screening should watch the low-residual tail (surplus-VRE, negative-
price hours), not only the winter peak, because that's the end of the curve
that's actually changing.

Metric: percentiles of hourly residual by year (MW). Period: 2019–2025.
(`sql/findings/residual_load.sql: residual_duration_by_year`,
`residual_below_zero_by_year`.)

| year | peak | p95 | p75 | p50 | p25 | p05 | trough | hrs < 0 |
|---|---|---|---|---|---|---|---|---|
| 2019 | 74,639 | 57,584 | 46,415 | 38,151 | 29,574 | 16,077 | 2,544 | 0 |
| 2020 | 72,275 | 55,734 | 43,571 | 35,407 | 27,004 | 14,345 | 2,440 | 0 |
| 2021 | 70,465 | 59,137 | 47,976 | 39,777 | 31,417 | 17,704 | 3,626 | 0 |
| 2022 | 70,964 | 55,032 | 42,764 | 34,648 | 25,905 | 12,821 | 1,882 | 0 |
| 2023 | 67,958 | 52,196 | 39,082 | 29,503 | 20,117 | 7,365 | −5,647 | 51 |
| 2024 | 67,251 | 51,889 | 39,265 | 30,604 | 20,904 | 6,590 | −8,324 | 75 |
| 2025 | 68,276 | 53,689 | 40,241 | 30,536 | 19,115 | 3,392 | −8,443 | 202 |

The curve steepens from the bottom. The top three quartiles drift down modestly,
but p05 collapses from ~16 GW (2019) to ~3.4 GW (2025) and the trough goes deeply
negative from 2023 on. So the median hour got maybe 8 GW lighter while the
lightest hours got ~14 GW lighter — the spread is widening downward.

Within the day, solar carves a midday belly into what used to be a plateau
(`residual_profile_by_hour`). In 2019 residual sat around 35–45 GW through
daylight; by 2025 the 12:00–14:00 average is ~19 GW while the 19:00 evening peak
(~40 GW) is now the clear daily maximum. By season in 2025 the midday average is
7.9 GW in summer and 12.5 GW in spring but 35.5 GW in winter
(`residual_midday_vs_evening_2025`) — the sun sets the daytime floor three
seasons out of four, and winter is where residual, and system stress, still
concentrate.

Caveat: residual uses only load, wind and solar. SMARD fully measures generation
across all zones only for wind offshore and nuclear; onshore wind and solar look
better covered than the conventional fuels but aren't independently audited here,
so treat the residual level as good-to-a-few-percent, not exact. The by-year
split is deliberate — a single pooled curve would hide the pivot.

---

## 2. Price by pressure: level and spike risk climb together

**Headline.** Median day-ahead price rises from €4/MWh in the loosest residual
decile to €110/MWh in the tightest, but the mean rises faster (€15 to €153) —
the top decile is where both the price level and the spike tail live. **Decision
it supports:** a residual-pressure decile is a usable spike-screening signal, and
negative prices are almost entirely a bottom-decile phenomenon, so the two tails
want separate flags.

Metric: day-ahead price (EUR/MWh, DE-LU) across residual decile (NTILE 1–10 over
the whole window). Period: 2019–2025.
(`sql/findings/price_by_pressure.sql: price_by_residual_decile`.)

| decile | median € | mean € | net-importer % | neg-price % | avg VRE cov |
|---|---|---|---|---|---|
| 1 | 4.4 | 14.6 | 7.8 | 31.8 | 0.82 |
| 2 | 55.0 | 55.1 | 30.2 | 1.5 | 0.62 |
| 3 | 74.4 | 77.1 | 39.2 | 0.0 | 0.51 |
| 4 | 81.3 | 87.4 | 44.0 | 0.0 | 0.42 |
| 5 | 88.1 | 99.6 | 49.5 | 0.0 | 0.35 |
| 6 | 91.5 | 106.1 | 54.7 | 0.0 | 0.30 |
| 7 | 95.3 | 109.7 | 57.9 | 0.0 | 0.26 |
| 8 | 98.0 | 118.6 | 60.0 | 0.0 | 0.23 |
| 9 | 101.4 | 126.5 | 61.8 | 0.0 | 0.19 |
| 10 | 110.4 | 152.7 | 62.1 | 0.0 | 0.14 |

The mean pulls well above the median only at the top, and the reason is the tail,
not the centre. In decile 10 the median is €110 but the 95th percentile is €418
and the max is €936; in decile 1 the median is €4 but the 95th percentile is
still €73 (`price_spike_tail`). Tight hours are reliably expensive and
occasionally extreme; loose hours are reliably cheap and only rarely spike.

Negative prices sit at the other end. Of 2,048 negative-price hours in the
window, 1,954 (95%) fall in decile 1 and 94 in decile 2, none above
(`negative_price_concentration`) — negative pricing is a surplus-VRE event, which
is why decile 1 pairs a €4 median with a 32% negative-price rate and 0.82 average
VRE coverage.

Caveat: deciles are pooled over 2019–2025, so a decile-1 hour in 2019 and one in
2025 don't sit at the same absolute residual — the ranking is within the whole
window, not within a year. Price is the DE-LU day-ahead auction only.

---

## 3. Import reliance: a commercial position that flipped in 2023

**Headline.** Germany's commercial trade balance flipped from net exporter to net
importer in 2023 — net-importer days jumped from 99 (2022) to 213 (2023) to 281
(2024), and the annual balance swung from 27 TWh net exported in 2022 to 12 / 28 /
22 TWh net imported in 2023–2025, lining up in time with the April-2023 nuclear
phase-out. **Decision it supports:** treat import reliance as a market-coupling
signal that concentrates in high-residual, low-VRE, evening hours — a commercial
position, not a statement about physical adequacy.

Metric: net-importer days and signed annual net-import energy (TWh; + = net
importer). Period: 2019–2025.
(`sql/findings/import_reliance.sql: net_import_days_by_year`.)

| year | net-importer days | net import (TWh) |
|---|---|---|
| 2019 | 96 | −35.10 |
| 2020 | 113 | −18.42 |
| 2021 | 113 | −17.80 |
| 2022 | 99 | −26.85 |
| 2023 | 213 | +11.73 |
| 2024 | 281 | +28.33 |
| 2025 | 271 | +21.92 |

The commercial position tracks supply pressure cleanly. Net-importer share rises
across residual deciles from 8% (decile 1) to 62% (decile 10) — see finding 2 —
and falls monotonically with VRE coverage, from 75% of hours below 0.2 coverage
to under 1% above 0.8 (`net_importer_share_by_vre_band`). Within the day the
pattern survives even in the import-heavy years: in 2025 the net-importer share
is 83–84% in the evening ramp (18:00–20:00) but dips to ~41% at midday when solar
is covering load, versus 7–8% at those same midday hours in 2019
(`net_importer_share_by_hour`). Seasonally, pooled over the window, summer hours
are in net-import position most often (66%) and winter least (25%)
(`net_importer_share_by_season`) — cheap neighbouring supply competes hardest
when domestic residual is lowest.

Caveat: this is the commercial (traded / market-coupled) net position stitched
from SMARD 661 then 4629, with `net_import = −commercial_net_export`. Physical
interconnector flow (714) is deliberately excluded. A net-import hour means
importing was economic that hour, not that Germany physically ran short — read it
as a market signal, not an adequacy verdict. The 2023 sign flip coincides with
the nuclear phase-out in time; the data shows association, not causation.

---

## 4. Forecast accuracy: next-day pressure is visible within a few percent

**Headline.** Whole-window day-ahead MAE is 3.8% of mean actual for load, 8.7%
for wind and 7.3% for solar; residual comes out at 2,548 MW (7.6%) because it
compounds the three. **Decision it supports:** the derived day-ahead residual is
good enough to screen next-day pressure, with wind the limiting component in
relative terms and the residual error concentrated at midday.

Metric: mean absolute error of day-ahead forecast vs actual (MW, and % of mean
actual). Period: 2019–2025. (`sql/findings/forecast_accuracy.sql: mae_overall`.)

| component | MAE (MW) | MAE (% of mean actual) |
|---|---|---|
| load | 2,075 | 3.8 |
| wind (on+offshore) | 1,283 | 8.7 |
| solar | 452 | 7.3 |
| residual (derived) | 2,548 | 7.6 |

Load is forecast most tightly; wind is the hardest in relative terms and drifts
slightly worse over the window (8.4% in 2020 to 9.1% in 2025,
`relative_mae_by_year`). Residual is the largest miss in absolute MW because its
error is the sum of the load, wind and solar errors, and its relative error
climbs from 6.4% (2020) to 8.8% (2025) as the mix shifts and the mean residual
falls (`mae_by_year`, `relative_mae_by_year`).

Solar needs a careful reading. Its absolute MAE roughly doubled, 333 MW (2019) to
677 MW (2025) (`mae_by_year`), but that tracks the growing PV fleet, not a
degrading method: restricted to daylight hours (actual solar > 500 MW) the
relative MAE is flat at roughly 7–8% across the whole window
(`solar_mae_daylight_relative_by_year`). Bigger fleet, same proportional error.

The misses have a clear shape. By month, load error peaks in January (3,032 MW)
and solar error peaks in spring (April 627 MW), so residual error is worst in
January (3,560 MW) (`mae_by_month`). By hour, solar error is a midday bulge —
about 4 MW overnight rising to ~1,400 MW at 12:00–13:00 — which drives residual
error to its own midday peak near 3,100 MW, while load and wind stay flatter
across the clock (`mae_by_hour`). If a day-ahead residual call is going to be
wrong, it's most likely wrong around midday in winter.

Caveat: this assumes the stored forecast columns are the genuine as-published
day-ahead values known at gate closure, not later revisions — flagged but not yet
fully verified (methodology, open question 8). The residual forecast is derived
(`fc_load − fc_wind − fc_solar`) to match the realised residual definition, not a
SMARD-published series.

---

## Notes and open ends

These don't change the findings but bound them. The 2025 reconciliation against
the Bundesnetzagentur press release passes (generation 437.9 vs 437.6 TWh,
average day-ahead €89.32 exact, net imports 21.92 vs 21.9 TWh, 573 negative-price
hours exact), but it's a script, not yet a CI gate — `data/` is gitignored, so
wiring it in needs a small design choice about fixtures. Two minor series items
stay open in the docs: pumped-storage consumption (4387) and a Download-Center
reconfirm of the retired 661 commercial-trade series. Neither touches the columns
these four findings rest on.

To reproduce every number above: `python scripts/run_findings.py` (or pass a file
stem, e.g. `run_findings.py price_by_pressure`).
