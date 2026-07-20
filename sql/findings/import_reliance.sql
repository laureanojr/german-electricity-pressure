-- Findings: import reliance as a COMMERCIAL position.
-- net_import = -commercial_net_export, stitched from SMARD 661 (2019 -> 2020-12-31)
-- and 4629 (2021 -> present). This is the market-coupling / traded position, not
-- physical interconnector flow (714 is excluded on purpose). A net-import hour or
-- day means importing was economic, not that Germany physically ran short.

-- name: net_import_days_by_year
-- Net-importer days per year and the annual signed net-import energy (TWh;
-- positive = net importer, negative = net exporter). The 2023 sign flip lines up
-- in time with the nuclear phase-out.
SELECT
    year,
    count(*) FILTER (WHERE net_importer_day) AS net_importer_days,
    round(sum(net_import_mwh) / 1e6, 2)      AS net_import_twh
FROM mart_daily_summary
GROUP BY year
ORDER BY year;

-- name: net_importer_share_by_hour
-- Share of hours in net-import position by local hour, 2019 vs 2025. Midday
-- (solar) is the daily low even in 2025; the evening ramp is the high.
SELECT
    hour_local,
    round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END) FILTER (WHERE year = 2019)) AS pct_2019,
    round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END) FILTER (WHERE year = 2025)) AS pct_2025
FROM mart_conditions_hourly
GROUP BY hour_local
ORDER BY hour_local;

-- name: net_importer_share_by_season
-- Share of hours in net-import position by season, whole window.
SELECT
    season,
    round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1) AS net_importer_pct
FROM mart_conditions_hourly
GROUP BY season
ORDER BY net_importer_pct DESC;

-- name: net_importer_share_by_vre_band
-- Share of hours in net-import position by VRE coverage band, whole window.
-- Falls monotonically as wind + solar cover more of load.
SELECT
    CASE
        WHEN vre_coverage < 0.2 THEN '1: <0.2'
        WHEN vre_coverage < 0.4 THEN '2: 0.2-0.4'
        WHEN vre_coverage < 0.6 THEN '3: 0.4-0.6'
        WHEN vre_coverage < 0.8 THEN '4: 0.6-0.8'
        ELSE '5: >=0.8'
    END                                                            AS vre_band,
    count(*)                                                       AS hours,
    round(100.0 * avg(CASE WHEN net_import_flag THEN 1 ELSE 0 END), 1) AS net_importer_pct
FROM mart_conditions_hourly
GROUP BY vre_band
ORDER BY vre_band;
