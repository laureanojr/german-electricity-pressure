"""Registry of the in-scope SMARD series.

IDs and names are confirmed against SMARD's own app config
(``market_data_configuration.json``) and the user manual — see
``docs/data_dictionary.md`` [CFG]/[M]. Do not edit an ID here without
re-confirming it against that config.

Two rules drive the ``kind`` field, both official (manual §2 / §D):
  * ``energy``  -> values are electrical work in MWh; aggregate 15-min -> hour
                  by SUM (and a missing sub-interval makes the hour a gap).
  * ``price``   -> EUR/MWh, a rate; aggregate by MEAN, never sum.
"""

from __future__ import annotations

from dataclasses import dataclass

# Project window (inclusive). Full calendar years after the 2018 bidding-zone
# split, per Part B of the project spec.
WINDOW_START = "2019-01-01"
WINDOW_END = "2025-12-31"

# SMARD chart-data host. Weekly JSON files, see docs/data_dictionary.md.
CHART_DATA_HOST = "https://www.smard.de/app/chart_data"


@dataclass(frozen=True)
class SmardSeries:
    """One downloadable SMARD chart-data series.

    key         short snake_case column name used inside the pipeline
    data_id     SMARD chart_data filter id (confirmed [CFG])
    name        official SMARD name (German)
    region      "DE" (country) or "DE-LU" (bidding zone)
    resolution  native resolution to download: "quarterhour" or "hour"
    kind        "energy" (MWh, agg=sum) or "price" (EUR/MWh, agg=mean)
    role        grouping for docs/analysis; not used by the maths
    """

    key: str
    data_id: int
    name: str
    region: str
    resolution: str
    kind: str
    role: str

    @property
    def agg(self) -> str:
        return "sum" if self.kind == "energy" else "mean"


# --- Demand -----------------------------------------------------------------
LOAD = SmardSeries("load", 410, "Stromverbrauch: Gesamt (Netzlast)",
                   "DE", "quarterhour", "energy", "demand")

# SMARD's own realised residual load, kept only as a cross-check against the
# residual we compute ourselves (methodology item 5). Not a fact_hourly input.
RESIDUAL_SMARD = SmardSeries("residual_load_smard", 4359,
                             "Stromverbrauch: Residuallast",
                             "DE", "quarterhour", "energy", "validation")

# --- Generation (realised) --------------------------------------------------
GENERATION = [
    SmardSeries("wind_onshore", 4067, "Stromerzeugung: Wind Onshore",
                "DE", "quarterhour", "energy", "vre"),
    SmardSeries("wind_offshore", 1225, "Stromerzeugung: Wind Offshore",
                "DE", "quarterhour", "energy", "vre"),
    SmardSeries("solar", 4068, "Stromerzeugung: Photovoltaik",
                "DE", "quarterhour", "energy", "vre"),
    SmardSeries("lignite", 1223, "Stromerzeugung: Braunkohle",
                "DE", "quarterhour", "energy", "conventional"),
    SmardSeries("hard_coal", 4069, "Stromerzeugung: Steinkohle",
                "DE", "quarterhour", "energy", "conventional"),
    SmardSeries("gas", 4071, "Stromerzeugung: Erdgas",
                "DE", "quarterhour", "energy", "conventional"),
    SmardSeries("biomass", 4066, "Stromerzeugung: Biomasse",
                "DE", "quarterhour", "energy", "context"),
    SmardSeries("hydro", 1226, "Stromerzeugung: Wasserkraft",
                "DE", "quarterhour", "energy", "context"),
    SmardSeries("nuclear", 1224, "Stromerzeugung: Kernenergie",
                "DE", "quarterhour", "energy", "context"),
    SmardSeries("pumped_storage_gen", 4070, "Stromerzeugung: Pumpspeicher",
                "DE", "quarterhour", "energy", "context"),
    SmardSeries("other_conventional", 1227,
                "Stromerzeugung: Sonstige Konventionelle",
                "DE", "quarterhour", "energy", "context"),
    SmardSeries("other_renewable", 1228,
                "Stromerzeugung: Sonstige Erneuerbare",
                "DE", "quarterhour", "energy", "context"),
]

# --- Price ------------------------------------------------------------------
# Day-ahead auction price for the DE/LU bidding zone. A rate: aggregate by mean.
PRICE = SmardSeries("day_ahead_price", 4169,
                    "Grosshandelspreis: Deutschland/Luxemburg",
                    "DE-LU", "hour", "price", "price")

# --- Commercial cross-border trade -----------------------------------------
# Commercial net export ("Kommerzieller Nettoexport", +export / -import) is one
# concept served by two data_ids that change over at end-2020. Both are
# hourly-native here, so no sub-hour aggregation is needed. See the cross-border
# section of docs/data_dictionary.md.
COMMERCIAL_NETEXPORT_OLD = SmardSeries(
    "commercial_net_export_old", 661, "Kommerzieller Nettoexport (bis 2020)",
    "DE", "hour", "energy", "trade")
COMMERCIAL_NETEXPORT_NEW = SmardSeries(
    "commercial_net_export_new", 4629, "Kommerzieller Nettoexport (ab 2020-11)",
    "DE", "hour", "energy", "trade")

# Stitch rule: use the old series strictly before this UTC instant, the new one
# on/after it. The two overlap Nov-Dec 2020, so 2021-01-01 sits safely inside
# the new series' coverage. (docs/data_dictionary.md, cross-border build rule.)
COMMERCIAL_STITCH_BOUNDARY = "2021-01-01"

# Columns whose sum defines residual load. Residual = load - these.
# Stated explicitly so the definition lives in exactly one place
# (methodology "decisions"): wind + solar only, not hydro/biomass.
VRE_FOR_RESIDUAL = ("wind_onshore", "wind_offshore", "solar")


def raw_series() -> list[SmardSeries]:
    """Every series to physically download (order is stable/deterministic)."""
    return [
        LOAD,
        RESIDUAL_SMARD,
        *GENERATION,
        PRICE,
        COMMERCIAL_NETEXPORT_OLD,
        COMMERCIAL_NETEXPORT_NEW,
    ]


def fact_energy_columns() -> list[str]:
    """Energy columns that land in fact_hourly (load + all generation)."""
    return [LOAD.key] + [s.key for s in GENERATION]
