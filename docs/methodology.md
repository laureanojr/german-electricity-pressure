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

1. **Which numeric filter ID is which series — officially.** I have official *names* [M §D] and I
   probe-verified a handful of IDs on the live host [API], but the authoritative name↔ID binding
   lives in the Download Center's JavaScript UI, which I could not load this session. So the
   realised-generation IDs in the dictionary are still *unconfirmed*. Until I confirm them against
   the Download Center, I won't hard-code them. [inference on the gap; official names M §D]

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

## What Step 1 must close before moving on

- Confirm the filter ID ↔ name bindings against the official Download Center (items 1, plus the
  forecast-residual ID and the realised-generation IDs).
- Resolve commercial cross-border coverage for 2019–2025 via the Download Center — this blocks one
  of the four analyses.
- Confirm price granularity across the window and lock the aggregation (item 3).
- Verify the historical forecast columns are the as-published day-ahead values (item 8).
- Quantify the conventional-generation under-coverage well enough to caveat residual load (item 2).
- Write the one-line defence for the residual-load boundary (item 5).

Only then does `fact_hourly` deserve the claim "you can query any hour and trust the units."
