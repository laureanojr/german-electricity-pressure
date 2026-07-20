-- Findings: day-ahead forecast accuracy.
-- fact_forecast_hourly holds forecast_/actual_ for load, wind (onshore+offshore),
-- solar and residual, with error_* = forecast - actual (positive = over-forecast).
-- residual forecast is derived (fc_load - fc_wind - fc_solar) to match the
-- realised residual definition, so its error compounds the other three.
-- MAE = mean(|error|) in MW. "load" is a reserved word in DuckDB, hence mae_load.

-- name: mae_overall
-- Whole-window MAE per component (MW) and as a share of each component's mean
-- actual, so absolute and relative error sit side by side.
SELECT
    round(avg(abs(error_load)))                                  AS mae_load,
    round(100 * avg(abs(error_load)) / avg(actual_load), 1)      AS load_pct,
    round(avg(abs(error_wind)))                                  AS mae_wind,
    round(100 * avg(abs(error_wind)) / avg(actual_wind), 1)      AS wind_pct,
    round(avg(abs(error_solar)))                                 AS mae_solar,
    round(100 * avg(abs(error_solar)) / avg(actual_solar), 1)    AS solar_pct,
    round(avg(abs(error_residual)))                              AS mae_residual,
    round(100 * avg(abs(error_residual)) / avg(actual_residual), 1) AS residual_pct
FROM fact_forecast_hourly;

-- name: mae_by_year
-- MAE per component by year (MW), plus mean residual error as a bias check
-- (sign = systematic over/under-forecast of residual).
SELECT
    year,
    round(avg(abs(error_load)))     AS mae_load,
    round(avg(abs(error_wind)))     AS mae_wind,
    round(avg(abs(error_solar)))    AS mae_solar,
    round(avg(abs(error_residual))) AS mae_residual,
    round(avg(error_residual))      AS residual_bias
FROM fact_forecast_hourly
GROUP BY year
ORDER BY year;

-- name: relative_mae_by_year
-- Relative MAE (% of mean actual) by year. Separates a growing fleet (bigger
-- absolute error) from a degrading method (bigger relative error).
SELECT
    year,
    round(100 * avg(abs(error_load)) / avg(actual_load), 1)      AS load_pct,
    round(100 * avg(abs(error_wind)) / avg(actual_wind), 1)      AS wind_pct,
    round(100 * avg(abs(error_solar)) / avg(actual_solar), 1)    AS solar_pct,
    round(100 * avg(abs(error_residual)) / avg(actual_residual), 1) AS residual_pct
FROM fact_forecast_hourly
GROUP BY year
ORDER BY year;

-- name: solar_mae_daylight_relative_by_year
-- Solar MAE relative to mean actual over daylight hours only (actual_solar > 500
-- MW), so overnight zeros don't flatter the ratio. Roughly flat while absolute
-- MAE doubles -> the fleet grew, the forecast didn't get worse per unit.
SELECT
    year,
    round(avg(abs(error_solar)))                              AS mae_solar,
    round(100 * avg(abs(error_solar)) / avg(actual_solar), 1) AS solar_pct_daylight
FROM fact_forecast_hourly
WHERE actual_solar > 500
GROUP BY year
ORDER BY year;

-- name: mae_by_month
-- MAE per component by calendar month (whole window, MW). Load worst in winter,
-- solar worst in the long-daylight months.
SELECT
    month,
    round(avg(abs(error_load)))     AS mae_load,
    round(avg(abs(error_wind)))     AS mae_wind,
    round(avg(abs(error_solar)))    AS mae_solar,
    round(avg(abs(error_residual))) AS mae_residual
FROM fact_forecast_hourly
GROUP BY month
ORDER BY month;

-- name: mae_by_hour
-- MAE per component by local hour of day (whole window, MW). Solar error is a
-- midday bulge (zero overnight); wind and load are flatter across the clock.
SELECT
    hour_local,
    round(avg(abs(error_load)))     AS mae_load,
    round(avg(abs(error_wind)))     AS mae_wind,
    round(avg(abs(error_solar)))    AS mae_solar,
    round(avg(abs(error_residual))) AS mae_residual
FROM fact_forecast_hourly
GROUP BY hour_local
ORDER BY hour_local;
