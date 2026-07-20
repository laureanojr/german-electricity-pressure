# Data dictionary — SMARD source series

**Source:** SMARD (Bundesnetzagentur), CC BY 4.0. Attribution required as
"Bundesnetzagentur | SMARD.de". [DU]

**Provenance rule for this file:** every factual line is tagged to where it was learned. If a
statement has no official-SMARD tag, it is explicitly marked *unconfirmed* and must not be
relied on until checked against an official SMARD source. Tags:

- **[M]** — SMARD User manual (Benutzerhandbuch), Feb 2024, official PDF, section noted.
  `https://www.smard.de/resource/blob/212924/61a75e052eddb43a8d3cc4c6e1653fa3/smard-benutzerhandbuch-02-2024-data.pdf`
- **[DU]** — SMARD "Data use" page. `https://www.smard.de/en/datennutzung`
- **[WF]** — SMARD wiki "Forecast data". `https://www.smard.de/page/en/wiki-article/5884/206318/forecast-data`
- **[WC]** — SMARD wiki "Cross-border electricity trade". `https://www.smard.de/page/en/wiki-article/6076/6012/cross-border-electricity-trade`
- **[WC-DE]** — SMARD wiki (DE) "Stromhandel und physikalischer Stromfluss", whose official
  "Marktdaten" deep-link lists the commercial category (prefix 22, incl. module 22000661) and the
  physical series 31000714. `https://www.smard.de/page/home/wiki-article/446/596/stromhandel-und-physikalischer-stromfluss`
- **[WP]** — SMARD wiki "Electricity trade and physical flow of electricity". `https://www.smard.de/page/en/wiki-article/5884/6140/electricity-trade-and-physical-flow-of-electricity`
- **[API]** — Value observed directly from the official chart-data host on `smard.de` (exact URL given).
- **[CFG]** — SMARD's own application config, official:
  `https://www.smard.de/app/chart_configuration/market_data_configuration.json`. This is the
  authoritative name↔ID map: each module carries `"data_id"` (= the chart_data filter),
  `"name"`, `"unit"`, `"source_resolution"`, and category. Read live from smard.de.
- **[enum-unofficial]** — third-party `bundesAPI/deutschland` GitHub client. Superseded by [CFG];
  no longer relied on below.

**Project window:** 2019-01-01 → 2025-12-31, hourly. Finest native grain is quarter-hour. [M §2]

---

## How the data behaves (all officially sourced)

**Values are electrical work in MWh; quarter-hours are summed to the hour.** The manual states
the finest granularity is quarter-hour and that "quarter-hour values of electrical work [MWh]
belonging to a given hour are summed" to aggregate. [M §2] I also confirmed this on live data:
for total grid load, the hour beginning 2019-07-01 00:00 = `46029.5`, exactly the sum of its four
quarter-hour values `11723.25 + 11564.5 + 11444.75 + 11297.0`. [API `410/DE/410_DE_hour_1561932000000` and `..._quarterhour_...`]
→ **Aggregate energy series by sum, never mean.**

**Wholesale price is in €/MWh and is averaged, not summed.** The manual gives the wholesale price
in €/MWh [M §D] and states that for wholesale prices, mean values are formed per the selected
resolution. [M §C] Live price values that week ran ~€6.77–€53/MWh. [API `4169/DE-LU/..._hour_1561932000000`]
→ **Average the price across intervals; never sum it.**

**Times are CET/CEST (local), and each timestamp is an interval start.** "All times on SMARD
refer to Central European Standard Time (CET / UTC+1) or Central European Summer Time
(CEST / UTC+2)"; clocks skip 02:00–03:00 on the last Sunday in March and repeat 02:00–03:00 on
the last Sunday in October; a labelled time is the *start* of the interval. [M §1.4]
→ DST days therefore carry 23h/25h (92/96/100 quarter-hours). The JSON delivers these interval
starts as Unix-epoch-millisecond instants. [API — every file]

**A gap in any sub-interval makes the aggregate a gap.** "An aggregation is only performed when
all required data are available; if at least one gap exists, the aggregation is likewise counted
as a gap." [M §2] → don't expect SMARD to silently fill; expect explicit holes.

**Published values get revised, with no fixed schedule.** "All data on SMARD are updated when new
information becomes available… historical data can be recalculated more precisely… there is
fundamentally no fixed revision process… provisional data can later be replaced by
quality-assured data." [M §1.3] Consistent with this, the same 2019-week file carried different
`meta_data.created` stamps across series (Dec 2022 to 2026). [API — `created` field]
→ Record `created` at download; a later re-pull can change values.

**Data origin.** SMARD receives data from ENTSO-E; only data verified by the Bundesnetzagentur is
published, and quality is continuously improved with the TSOs. [DU]

**Regions.** The API host serves `DE` (country Germany) and `DE-LU` (the DE/LU bidding zone) among
others. [API — both return data] The DE/LU zone dates from 2018-10-01 (before that DE-AT-LU),
which is why a 2019 start sits cleanly inside a single zone definition. [WC context]

---

## Series in scope

> **On the numeric filter IDs.** These are now **officially confirmed.** SMARD's own app config
> [CFG] maps each `data_id` (= the chart_data filter) to its official name, unit, and source
> resolution. Every ID below is quoted from that file unless noted. Names are also in the manual
> [M §D]. (The earlier "unconfirmed / third-party enum" caveat is retired — [CFG] supersedes it.)

### Demand — official names [M §D 2.1]

| Series (EN / DE) | Filter ID | ID status | Grain | Unit |
|---|---|---|---|---|
| Total grid load / Stromverbrauch: Gesamt (Netzlast) | 410 | confirmed [CFG] + probe [API] | 15-min + hour | MWh |
| Residual load, realised / Stromverbrauch: Residuallast | 4359 | confirmed [CFG] + probe [API] | 15-min + hour | MWh |
| Pumped-storage consumption / Stromverbrauch: Pumpspeicher | 4387 | unconfirmed (not in [CFG] slice read) | 15-min + hour | MWh |

SMARD publishes a realised residual load of its own (4359). The project computes its own residual
(load − wind − solar); keep them separate. [M §D 2.1.2 defines Residuallast]

### Generation — filter IDs officially confirmed [CFG]

Every `data_id`→name below is quoted from `market_data_configuration.json` [CFG]. Realised
generation (category "Realisierte Erzeugung"); source resolution quarter-hour; unit MWh.

| Series (EN / DE) | Filter ID | Confirmed name [CFG] | Role |
|---|---|---|---|
| Wind onshore / Wind Onshore | 4067 | Wind Onshore | VRE (residual) |
| Wind offshore / Wind Offshore | 1225 | Wind Offshore | VRE (residual) |
| Solar / Photovoltaik | 4068 | Photovoltaik | VRE (residual) |
| Lignite / Braunkohle | 1223 | Braunkohle | Conventional |
| Hard coal / Steinkohle | 4069 | Steinkohle | Conventional |
| Natural gas / Erdgas | 4071 | Erdgas | Conventional |
| Biomass / Biomasse | 4066 | Biomasse | Context (renewable, not VRE) |
| Hydro / Wasserkraft | 1226 | Wasserkraft | Context |
| Nuclear / Kernenergie | 1224 | Kernenergie | Context (to ~0 after April 2023) |
| Pumped storage / Pumpspeicher | 4070 | Pumpspeicher | Context |
| Other conventional / Sonstige Konventionelle | 1227 | Sonstige Konventionelle | Context |
| Other renewable / Sonstige Erneuerbare | 1228 | Sonstige Erneuerbare | Context |

> **Coverage caveat — official and important.** Realised generation is *not* fully measured for
> every fuel. Full coverage by measurement across all control zones exists **only for Wind
> Offshore and Nuclear**. Biomass, hard coal, gas and "other conventional" are, in some control
> zones, not fully covered, so their realised generation is "systematically underestimated". [M §D 1]
> This directly affects conventional-generation totals and, by subtraction, any residual-load work.

### Price — official [M §D 3.1]

| Series (EN / DE) | Filter ID | ID status | Region | Grain | Unit |
|---|---|---|---|---|---|
| Day-ahead wholesale price / Großhandelspreis: Deutschland/Luxemburg | 4169 | probe-verified [API] | DE-LU | hour | €/MWh |

This is the day-ahead auction price for the DE/LU zone — not "the" electricity price. Name it
precisely. [M §D 3.1]

### Day-ahead forecasts — official [M §D 1.2 (generation), §D 2.2 (consumption); WF (timing)]

Forecasts are submitted by the four TSOs by 18:00 for the following day. [WF] The manual notes a
**granularity mismatch**: forecast *total* generation is published hourly in some regions, while
the wind/PV forecasts are quarter-hourly; "Other" forecast generation is a SMARD-computed
difference (total − wind/PV). [M §D 1.2]

| Series (EN / DE) | Filter ID | ID status | Grain | Notes |
|---|---|---|---|---|
| Forecast load / Prognostizierter Stromverbrauch: Gesamt (Netzlast) | 411 | probe-verified [API] | 15-min | 2019 forecast ≈ 10,648 vs realised ≈ 11,724 MWh/15-min — genuinely a forecast. [API] |
| Forecast total generation / Prognostizierte Erzeugung: Gesamt | 122 | probe-verified [API] | hour or 15-min by region [M §D 1.2] | |
| Forecast wind onshore / Prognostizierte Erzeugung: Wind Onshore | 123 | probe-verified [API] | 15-min | |
| Forecast wind offshore / Prognostizierte Erzeugung: Wind Offshore | 3791 | probe-verified [API] | 15-min | |
| Forecast solar / Prognostizierte Erzeugung: Photovoltaik | 125 | probe-verified [API] | 15-min | 0 overnight, bell curve by day. [API] |
| Forecast "other" generation / Sonstige Prognostizierte Stromerzeugung | 715 | unconfirmed [enum-unofficial] | — | SMARD-computed (total − wind/PV). [M §D 1.2] |
| Forecast residual load / Prognostizierter Stromverbrauch: Residuallast | — | ID not identified | 15-min | Exists as an official category [M §D 2.2.2]; ID not found. Or derive = fc load − fc wind − fc solar (match the realised-side definition). |

### Cross-border trade — **resolved** [CFG] confirms the identities; coverage stitches across the full window

The config settles which series is which [CFG]:

- **`data_id 4629` = "Kommerzieller Nettoexport" (Commercial net export)**, category "Kommerzieller
  Außenhandel", source resolution quarter-hour, unit MWh, regions incl. DE and DE-LU. [CFG]
- **`data_id 714` = "Physikalischer Nettoexport" (Physical net export)**, category "Physikalischer
  Stromfluss". [CFG] **Different concept — do not use for the commercial "import reliance" story,
  and never mix it with the commercial series.**

Both are signed (+ = net export, − = net import). [API]

**Commercial net export coverage — full 2019–2025 is achievable, but via two data_ids that
change over at end-2020 (same concept, "Kommerzieller Nettoexport"):**

| chart_data filter | Role | Coverage (bisected live) [API] |
|---|---|---|
| 661 | Older commercial net export (Kommerzieller Nettoexport; module `22000661` sits in the commercial category) [WC-DE] | **2019-01 → 2020-12-31.** Full 2019 data; ends at 2020-12-31 (null from 2021-01-01; empty in 2021). |
| 4629 | Current commercial net export [CFG] | **~2020-11 → present.** Null in 2019/most of 2020; data from mid-Nov 2020 onward (2025 present). |

They **overlap in Nov–Dec 2020**, so the join can be validated rather than assumed. In the overlap
they are close but not identical hour-by-hour (661 = 9076/7479/6806 vs 4629 = 9596/8689/8197 for
2020-12-28 00:00–02:00) [API] — expected, since they are two processing generations of the same
quantity (661 hourly-origin, 4629 quarter-hour-origin). Prefer one series per timestamp across the
seam; don't average them.

**Build rule.** Commercial net export for 2019–2025 = **661 for 2019-01-01 → 2020-12-31, then 4629
from 2021-01-01 → present** (validate against the Nov–Dec 2020 overlap). This keeps the whole
series a single consistent concept (commercial), so the import-reliance analysis can run the full
window. Physical flow (714 and its successors) stays out of that column.

> Note: `data_id 661` is not in the *current* config file (it's a retired series still served by
> the chart-data host); its commercial identity rests on the official German trade-page deep-link,
> where module `22000661` is listed under "kommerzieller Außenhandel" [WC-DE], plus its net-export
> value shape [API]. Worth a 5-minute reconfirm in the Download Center when convenient, but the
> commercial-vs-physical question itself is now settled by [CFG].

---

## Download rules (carry into the Step-1 script)

- Key every row on the interval-start instant; store as UTC, render Berlin local only for display; allow 23h/25h DST days. [M §1.4]
- Aggregate 15-min → hour by **sum** for energy (MWh); **average** the price. [M §2, §C]
- Treat any sub-interval gap as a gap in the aggregate. [M §2]
- Do **not** trust `index_*.json` for coverage: it is a generic 2014→2026 superset returned
  identically for every filter (observed on the API host); real coverage is null-vs-value in the
  data files. [API] After download, assert each in-scope series is non-null across the window and
  fail where it isn't — this is what exposed the cross-border gap.
- Record `meta_data.created` per file, since values can be revised with no fixed schedule. [M §1.3]
- Compute residual load yourself and state the definition next to any residual number; remember
  conventional fuels may be under-covered. [M §D 1]

## What is still NOT officially confirmed (do before trusting the build)

Most of the earlier gaps are now closed by the official config [CFG] and the cross-border
bisection. Remaining items:

- The **forecast-residual-load** filter ID (forecast side of Residuallast) — not yet pulled from
  [CFG]; either find it in the config or derive fc-residual = fc-load − fc-wind − fc-solar.
- `data_id 661`'s commercial label — settled well enough via [WC-DE] + values, but a 5-minute
  Download-Center reconfirm is cheap insurance.
- Pumped-storage consumption (4387) — not in the config slice read this session.
- Everything else (load, residual, all generation fuels, price, day-ahead forecasts, commercial
  net export 4629, physical net export 714) is confirmed via [CFG] and/or live probes.
