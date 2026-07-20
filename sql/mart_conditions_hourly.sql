-- mart_conditions_hourly: the analysis-ready "system pressure" table.
--
-- One row per UTC hour, derived from fact_hourly. Adds the observable
-- conditions the dashboard filters on: VRE coverage, residual-load decile,
-- price decile, net-import and negative-price flags, season, calendar.
--
-- Deciles use NTILE(10) window functions computed only over non-null rows
-- (via CTE + LEFT JOIN), so a gap in residual_load or price yields a NULL
-- decile rather than being mis-binned into decile 1. Deciles are computed over
-- the whole 2019-2025 window; the relationship is non-stationary (see
-- methodology), so dashboard views should still allow slicing by year.

WITH base AS (
    SELECT
        hour_ms, ts_utc, ts_local, date_local,
        year, month, hour_local, dow, is_weekend,
        CASE
            WHEN month IN (12, 1, 2) THEN 'winter'
            WHEN month IN (3, 4, 5)  THEN 'spring'
            WHEN month IN (6, 7, 8)  THEN 'summer'
            ELSE 'autumn'
        END AS season,
        load,
        wind_onshore, wind_offshore, solar,
        (wind_onshore + wind_offshore + solar) AS vre_generation,
        residual_load,
        (wind_onshore + wind_offshore + solar) / nullif(load, 0) AS vre_coverage,
        day_ahead_price,
        (day_ahead_price < 0) AS negative_price_flag,
        commercial_net_export,
        net_import,
        (net_import > 0) AS net_import_flag
    FROM fact_hourly
),

residual_deciles AS (
    SELECT
        hour_ms,
        ntile(10) OVER (ORDER BY residual_load) AS residual_decile
    FROM base
    WHERE residual_load IS NOT NULL
),

price_deciles AS (
    SELECT
        hour_ms,
        ntile(10) OVER (ORDER BY day_ahead_price) AS price_decile
    FROM base
    WHERE day_ahead_price IS NOT NULL
)

SELECT
    b.*,
    r.residual_decile,
    p.price_decile
FROM base b
LEFT JOIN residual_deciles r USING (hour_ms)
LEFT JOIN price_deciles p USING (hour_ms)
