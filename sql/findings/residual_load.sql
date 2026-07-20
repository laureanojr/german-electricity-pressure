-- Findings: residual load (load - wind onshore - wind offshore - solar).
-- residual_load is precomputed in fact_hourly / mart_conditions_hourly to the
-- project definition (wind + solar only); we never recompute it here so the
-- number always traces to the same column the build validated.
-- Relationships are non-stationary (nuclear to ~0 in April 2023, PV fleet still
-- growing), so everything that can move is reported by year.

-- name: residual_duration_by_year
-- Duration-curve shape as year-by-year percentiles of hourly residual (MW).
-- Reading the row left to right IS the duration curve: peak, then the value
-- exceeded 5% / 25% / 50% / 75% / 95% of hours, then the annual trough.
SELECT
    year,
    round(max(residual_load))                        AS peak,
    round(quantile_cont(residual_load, 0.95))        AS p95,
    round(quantile_cont(residual_load, 0.75))        AS p75,
    round(median(residual_load))                     AS p50,
    round(quantile_cont(residual_load, 0.25))        AS p25,
    round(quantile_cont(residual_load, 0.05))        AS p05,
    round(min(residual_load))                        AS trough
FROM fact_hourly
GROUP BY year
ORDER BY year;

-- name: residual_below_zero_by_year
-- Hours per year where wind + solar alone exceeded load (residual < 0), and the
-- share of the year that is. This is the bottom of the duration curve dropping
-- through zero; before 2023 it never does.
SELECT
    year,
    count(*) FILTER (WHERE residual_load < 0)                   AS hrs_below_zero,
    round(100.0 * avg(CASE WHEN residual_load < 0 THEN 1 ELSE 0 END), 2) AS pct_of_year
FROM fact_hourly
GROUP BY year
ORDER BY year;

-- name: residual_profile_by_hour
-- Average residual by local hour of day, 2019 vs 2025. Shows solar carving a
-- midday belly into what used to be a daytime plateau.
SELECT
    hour_local,
    round(avg(residual_load) FILTER (WHERE year = 2019)) AS avg_2019,
    round(avg(residual_load) FILTER (WHERE year = 2025)) AS avg_2025
FROM fact_hourly
GROUP BY hour_local
ORDER BY hour_local;

-- name: residual_profile_by_season
-- Average residual by season (whole window and 2025), plus the seasonal trough.
SELECT
    season,
    round(avg(residual_load))                        AS avg_all_years,
    round(avg(residual_load) FILTER (WHERE year = 2025)) AS avg_2025,
    round(min(residual_load))                        AS trough
FROM mart_conditions_hourly
GROUP BY season
ORDER BY avg_all_years DESC;

-- name: residual_midday_vs_evening_2025
-- 2025 only: how deep the midday residual sits versus the evening peak, by
-- season. Summer midday is where wind + solar most nearly cover load.
SELECT
    season,
    round(avg(residual_load) FILTER (WHERE hour_local BETWEEN 11 AND 14)) AS midday_11_14,
    round(avg(residual_load) FILTER (WHERE hour_local IN (18, 19, 20)))   AS evening_18_20
FROM mart_conditions_hourly
WHERE year = 2025
GROUP BY season
ORDER BY season;
