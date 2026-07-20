-- mart_daily_summary: one row per Berlin calendar day, for fast dashboard
-- rendering and headline stats. Rolls up mart_conditions_hourly.
--
-- Units discipline holds at the daily grain: energy (MWh) is SUMMED, price
-- (EUR/MWh) is AVERAGED, flags are COUNTED. n_hours is kept as an integrity
-- column and will read 23/24/25 across DST days.

SELECT
    date_local,
    min(year)          AS year,
    min(month)         AS month,
    any_value(season)  AS season,
    min(dow)           AS dow,
    bool_or(is_weekend) AS is_weekend,
    count(*)           AS n_hours,

    -- energy: daily totals (MWh)
    sum(load)           AS load_mwh,
    sum(wind_onshore)   AS wind_onshore_mwh,
    sum(wind_offshore)  AS wind_offshore_mwh,
    sum(solar)          AS solar_mwh,
    sum(vre_generation) AS vre_generation_mwh,
    sum(residual_load)  AS residual_load_mwh,
    sum(vre_generation) / nullif(sum(load), 0) AS vre_coverage,

    -- price (EUR/MWh): averaged, plus the daily range
    avg(day_ahead_price) AS avg_price,
    min(day_ahead_price) AS min_price,
    max(day_ahead_price) AS max_price,
    count(*) FILTER (WHERE negative_price_flag) AS negative_price_hours,

    -- commercial trade: signed daily net import and how many hours importing
    sum(net_import)      AS net_import_mwh,
    count(*) FILTER (WHERE net_import_flag) AS net_import_hours,
    (sum(net_import) > 0) AS net_importer_day

FROM mart_conditions_hourly
GROUP BY date_local
ORDER BY date_local
