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
- **[WP]** — SMARD wiki "Electricity trade and physical flow of electricity". `https://www.smard.de/page/en/wiki-article/5884/6140/electricity-trade-and-physical-flow-of-electricity`
- **[API]** — Value observed directly from the official chart-data host on `smard.de` (exact URL given).
- **[enum-unofficial]** — third-party `bundesAPI/deutschland` GitHub client. **Not an official
  SMARD source.** Used only to flag a candidate; never as proof.

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

> **On the numeric filter IDs.** Series *names and definitions* below are official [M]. The
> numeric `chart_data` filter IDs are an implementation detail of the SMARD web app and are **not
> published on any official SMARD page I could reach** (the Download Center, which shows the
> name↔ID binding, is a JavaScript app I could not load in this session). Where I fetched an ID
> and inspected its data, it is marked **probe-verified** (the values behave as the name implies,
> on the official API host). Where I have only the third-party enum, it is marked
> **unconfirmed — confirm in Download Center**. Do not hard-code an unconfirmed ID as fact yet.

### Demand — official names [M §D 2.1]

| Series (EN / DE) | Filter ID | ID status | Grain | Unit |
|---|---|---|---|---|
| Total grid load / Stromverbrauch: Gesamt (Netzlast) | 410 | probe-verified [API] | 15-min + hour | MWh |
| Residual load, realised / Stromverbrauch: Residuallast | 4359 | probe-verified [API] | 15-min + hour | MWh |
| Pumped-storage consumption / Stromverbrauch: Pumpspeicher | 4387 | unconfirmed [enum-unofficial] | 15-min + hour | MWh |

SMARD publishes a realised residual load of its own (4359). The project computes its own residual
(load − wind − solar); keep them separate. [M §D 2.1.2 defines Residuallast]

### Generation — official names and fuel list [M §D 1: Biomasse, Wind Offshore, Wind Onshore, Photovoltaik, Braunkohle, Steinkohle, Erdgas, Sonstige Erneuerbare, Wasserkraft, Kernenergie, Pumpspeicher, Sonstige Konventionelle]

All realised-generation filter IDs below are **unconfirmed [enum-unofficial]** — I did not probe
them this session and no official page binds them to names. Names are official [M §D 1].

| Series (EN / DE) | Candidate ID | Role |
|---|---|---|
| Wind onshore / Wind Onshore | 4067 | VRE (residual) |
| Wind offshore / Wind Offshore | 1225 | VRE (residual) |
| Solar / Photovoltaik | 4068 | VRE (residual) |
| Lignite / Braunkohle | 1223 | Conventional |
| Hard coal / Steinkohle | 4069 | Conventional |
| Natural gas / Erdgas | 4071 | Conventional |
| Biomass / Biomasse | 4066 | Context (renewable, not VRE) |
| Hydro / Wasserkraft | 1226 | Context |
| Nuclear / Kernenergie | 1224 | Context (to ~0 after April 2023) |
| Pumped storage / Pumpspeicher | 4070 | Context |
| Other conventional / Sonstige Konventionelle | 1227 | Context |
| Other renewable / Sonstige Erneuerbare | 1228 | Context |

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

### Cross-border trade — official names [M §D 3.2 Kommerzieller Außenhandel; WC/WP], coverage **unresolved**

| Series (EN / DE) | Filter ID | ID status | Grain | Notes |
|---|---|---|---|---|
| Commercial net export / Kommerzieller Außenhandel: Nettoexport | 4629 | probe-verified for 2025 only [API] | hour | +export / −import (2025 values −11 to +13 GWh). **All-null for the 2019 week tested**, on DE and DE-LU. [API] |

Two things to flag:

1. **Commercial ≠ physical.** Commercial foreign trade is the traded (market-coupling) position,
   supplied hourly and updated after each intraday session; the physical cross-border flow is a
   separate, distinct category. [WC, WP] Commercial is the right series for an "import reliance"
   read (a commercial position, not a physical-adequacy signal). Do not switch between them.
2. **Coverage gap — open.** Filter 4629 returned real 2025 data but was all-null for the 2019
   week on both regions. [API] So commercial net export back to 2019 is **not confirmed available
   via this endpoint**. **Open task:** source commercial foreign trade for the full window from
   the official Download Center and confirm the exact series/ID that spans 2019–2025.

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

- The numeric filter ID ↔ name binding for every series (needs the official Download Center).
- The realised-generation IDs (1223/4067/… — unprobed and unofficial this session).
- The forecast-residual-load filter ID.
- Commercial cross-border coverage for 2019–2025.
