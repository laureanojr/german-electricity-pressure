-- Findings: day-ahead price across supply pressure.
-- Pressure is proxied by residual_decile (NTILE 1..10 over the whole window,
-- computed in mart_conditions_hourly; decile 1 = lowest residual = most VRE
-- headroom, decile 10 = tightest). day_ahead_price is EUR/MWh for the DE-LU
-- bidding zone and is already an hourly mean in fact_hourly.

-- name: price_by_residual_decile
-- The headline table: per decile, the typical price (median), the average that
-- the spike tail pulls up (mean), how often Germany is a commercial net importer,
-- how often the price is negative, and the average VRE coverage in that decile.
SELECT
    residual_decile,
    round(median(day_ahead_price), 1)                                   AS median_price,
    round(avg(day_ahead_price), 1)                                      AS mean_price,
    round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1)  AS net_importer_pct,
    round(100.0 * avg(CASE WHEN negative_price_flag THEN 1 ELSE 0 END), 1) AS neg_price_pct,
    round(avg(vre_coverage), 2)                                         AS avg_vre_coverage
FROM mart_conditions_hourly
WHERE residual_decile IS NOT NULL
  AND day_ahead_price IS NOT NULL
GROUP BY residual_decile
ORDER BY residual_decile;

-- name: price_spike_tail
-- Why mean >> median in decile 10: the distribution, not just its centre.
-- Median, mean, 95th percentile and max for the loosest and tightest deciles.
SELECT
    residual_decile,
    round(median(day_ahead_price), 1)                     AS median_price,
    round(avg(day_ahead_price), 1)                        AS mean_price,
    round(quantile_cont(day_ahead_price, 0.95), 1)        AS p95_price,
    round(max(day_ahead_price), 1)                        AS max_price
FROM mart_conditions_hourly
WHERE residual_decile IN (1, 10)
  AND day_ahead_price IS NOT NULL
GROUP BY residual_decile
ORDER BY residual_decile;

-- name: negative_price_concentration
-- Where the window's negative-price hours actually sit by pressure decile.
-- Nearly all are in decile 1 (deepest VRE headroom); none above decile 2.
SELECT
    residual_decile,
    count(*) FILTER (WHERE negative_price_flag) AS negative_price_hours
FROM mart_conditions_hourly
WHERE negative_price_flag
GROUP BY residual_decile
ORDER BY residual_decile;
