# Methodology — Step 1 notes and open questions

Point of this file: distrust the data first, and write down every gap before building anything.
Same provenance rule as the data dictionary — a claim I state as *fact* is tagged to an official
SMARD source; anything I can't source is labelled as inference or an open question, not asserted.

Source tags (full URLs in `data_dictionary.md`): **[M]** user manual · **[DU]** data-use page ·
**[WF]** forecast-data wiki · **[WC]** cross-border-trade wiki · **[WP]** trade-vs-physical wiki ·
**[API]** value observed on the official `smard.de` chart-data host · **[inference]** my own
reasoning, not an official statement.

## Decisions I can defend, each with a source

- **Aggregate energy (MWh) by summing quarter-hours to the hour.** Official: values are electrical
  work in MWh and quarter-hour values within an hour are summed. [M §2] Also confirmed on live
  load data (hour = exact sum of its four quarter-hours). [API]
- **Average the price, never sum it.** Official: wholesale price is €/MWh and mean values are
  formed per resolution. [M §D, §C]
- **UTC key, local display, DST-aware.** Official: all SMARD times are CET/CEST, timestamps are
  interval starts, and DST skips/repeats an hour. [M §1.4]
- **Use commercial foreign trade (not physical flow) for import reliance**, framed as a commercial
  position. Official: the two are distinct categories; commercial is the traded/market-coupling
  position. [WC, WP]
- **Compute residual myself as load − wind − solar** and state it every time. The realised
  Residuallast that SMARD publishes is a separate official series [M §D 2.1.2]; I use my own and
  may cross-check against SMARD's.

## Things I genuinely don't understand yet (and why each matters)

1. **Which numeric filter ID is which series — RESOLVED.** SMARD's own app config
   `market_data_configuration.json` [CFG] is the authoritative name↔ID map: every module lists its
   `data_id` (= chart_data filter), name, unit and source resolution. All in-scope IDs are now
   confirmed there (load, residual, every generation fuel, commercial vs physical net export).
   Filter tag [CFG] added to the data dictionary. (Still to pull from [CFG]: the forecast-residual
   ID; and 4387 pumped-storage consumption.)

2. **How badly does incomplete generation coverage bias residual load?** Official: realised
   generation is fully measured across all zones **only for Wind Offshore and Nuclear**; biomass,
   hard coal, gas and "other conventional" are under-covered in some zones and therefore
   "systematically underestimated". [M §D 1] Wind and solar (my residual inputs) look better
   covered, but I don't yet know the magnitude of the conventional under-coverage or whether it
   moves over time — and it feeds every conventional-generation statement in the project.

3. **Is the day-ahead price one hourly product across the whole window?** I treated 4169 as hourly
   €/MWh. [API, M §D] I do *not* yet know whether 15-minute day-ahead pricing appears late in the
   window, which would mix two products in the price-by-pressure deciles. Needs checking. [inference]

4. **The forecast granularity mismatch.** Official: forecast *total* generation is hourly in some
   regions while wind/PV forecasts are quarter-hourly, and "other" forecast is a computed
   difference. [M §D 1.2] So building a clean quarter-hour forecast-vs-actual comparison isn't
   free — I have to align grains deliberately and decide how to treat the hourly-only pieces.

5. **What exactly belongs in "residual load"?** I draw the line at wind + solar (weather-driven,
   price-setting VRE). Hydro run-of-river and biomass are also largely must-run, so a reviewer
   using "load minus all renewables" will get a different number. This is a modelling choice, not
   the only definition — I need the one-line defence ready. [inference; SMARD's own Residuallast
   definition M §D 2.1.2 differs and is worth reading before I finalise mine.]

6. **What does "net import" actually establish?** Commercial net export comes from market coupling
   — where trading was economic, not where Germany physically ran short. [WC] A negative value in a
   high-residual hour is suggestive, not proof of inadequacy. The "imports = backup sourcing"
   interview bridge is an analogy [inference], and I'll keep saying so.

7. **How often do commercial and physical positions disagree?** Official: traded volumes and
   measured interconnector flows differ (loop flows, congestion management). [WP] I don't yet know
   how often, for Germany, the two disagree in *direction* — which decides whether every "Germany
   imported" sentence needs the qualifier "commercially".

8. **Are the historical forecasts the values actually published day-ahead, or later revisions?**
   Official: there's no fixed revision process and provisional data can be replaced by
   quality-assured data. [M §1.3] For forecast-accuracy to mean anything, the "forecast" column
   must be the genuine day-ahead value known at gate closure, not something recomputed later. I
   need to check this against the `created` stamps and the day-ahead-vs-intraday split. [inference]

9. **How much do recent values move on a re-pull?** Official basis for the concern: revisions
   happen with no fixed schedule, and I saw the same 2019 file re-created across different years.
   [M §1.3, API] I don't yet know how large the drift is for recent vs old periods — which affects
   whether my 2025 reconciliation against Bundesnetzagentur headline totals is stable or depends
   on the pull date.

10. **Structural breaks inside the window.** Nuclear went to zero in April 2023, and coal capacity
    fell over 2019–2025. [inference — widely known, verify against the data itself] These aren't
    data errors, but they mean the residual-load↔price relationship is almost certainly not
    stationary, so any single pooled statistic hides a moving system. Plan to report by year and
    expect the relationship to shift.

11. **Silent definitional changes per series.** Coverage methods differ by fuel and zone and are
    "continuously improved" with the TSOs. [M §D 1, DU] A quiet change in coverage or a category
    could look like a real trend. Worth a month-over-month sanity scan per series before trusting
    any long-run comparison. [inference]

## 2025 reconciliation (the sanity check with teeth)

`scripts/reconcile_2025.py` compares completed-2025 aggregates from `fact_hourly`
against Bundesnetzagentur's published figures [BNetzA-PR]. All four are within tolerance,
and it fails loudly if any drifts:

| Metric | `fact_hourly` | Official | Diff |
|---|---|---|---|
| Net electricity generation | 437.90 TWh | 437.6 TWh | +0.07% |
| Avg day-ahead price | €89.3219/MWh | €89.32/MWh | ~0 |
| Commercial net imports | 21.92 TWh | 21.9 TWh | +0.10% |
| Hours with negative price | 573 | 573 | exact |

**Definition pinned.** BNetzA's "actual generation" is **net electricity generation** — the
electricity fed into the general supply network *less* power plants' own consumption. It
excludes the Deutsche Bahn network, industrial and closed distribution networks, and
self-consumed household PV. [BNetzA-PR] That is exactly the sum of all twelve SMARD realised
generation categories, **pumped-storage output included** — including it is what makes the
total match (excluding it gives 428.0 TWh, ~10 TWh short). Per-source, the match is tight:

| | `fact_hourly` (TWh) | Official (TWh) |
|---|---|---|
| Renewables total | 257.76 | 257.5 |
| — onshore wind | 106.77 | 106.5 |
| — solar | 73.78 | 74.1 |
| — offshore wind | 26.20 | 26.1 |
| — biomass | 35.87 | 36.0 |
| Conventional total | 180.14 | 180.1 |
| — lignite | 67.17 | 67.2 |
| — gas | 60.55 | 60.6 |
| — hard coal | 28.16 | 28.2 |

**Residual explained.** The +0.3 TWh (0.07%) excess is data revision plus rounding, not a
definitional mismatch: official per-source figures are quoted to 0.1 TWh, the release is a
Jan-2026 snapshot, and SMARD data "may be updated on the basis of new findings" (also manual
§1.3). Per-source diffs are small and bidirectional (onshore +0.27, solar −0.32), consistent
with revision noise. The conventional total matches to 0.04 TWh.

Source: **[BNetzA-PR]** Bundesnetzagentur, "Bundesnetzagentur publishes 2025 electricity
market data", press release 2026-01-05.
`https://www.bundesnetzagentur.de/SharedDocs/Pressemitteilungen/EN/2026/20260104_SMARD.html`

## What Step 1 must close before moving on

- Filter ID ↔ name bindings — done via [CFG]. Left over: pull the forecast-residual ID and 4387
  from the config, and a cheap Download-Center reconfirm of the retired 661.
- Commercial cross-border coverage — **RESOLVED.** SMARD's config [CFG] confirms `4629` =
  "Kommerzieller Nettoexport" (commercial) and `714` = "Physikalischer Nettoexport" (physical).
  Commercial net export spans the full window via two data_ids of the *same* concept: **661
  (2019-01 → 2020-12-31) then 4629 (2021-01 → present)**, with a Nov–Dec 2020 overlap to validate
  the join. So the import-reliance analysis can keep the full 2019–2025 window — no scope cut
  needed — as long as it uses only the commercial series and never mixes in physical flow (714).
- Confirm price granularity across the window and lock the aggregation (item 3).
- Verify the historical forecast columns are the as-published day-ahead values (item 8).
- Quantify the conventional-generation under-coverage well enough to caveat residual load (item 2).
- Write the one-line defence for the residual-load boundary (item 5).

Only then does `fact_hourly` deserve the claim "you can query any hour and trust the units."
