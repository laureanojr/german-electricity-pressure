"""German electricity pressure dashboard (Streamlit).

A screening / reporting view over the four analyses in findings.md: residual
load, price by pressure, commercial import reliance, and day-ahead forecast
accuracy. Reads data/processed/gep.duckdb read-only; all SQL lives in
dashboard/queries.py so it can be tested without the UI.

Run:  streamlit run dashboard/app.py
This is a reporting tool, not a trading or dispatch tool. Findings are
observational (associations across 2019-2025), never causal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# `streamlit run dashboard/app.py` puts dashboard/ on sys.path, not the repo
# root, so make the package importable regardless of launch dir (same pattern as
# scripts/reconcile_2025.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import queries as q  # noqa: E402

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "gep.duckdb"

MAE_LABELS = {
    "mae_load": "Load",
    "mae_wind": "Wind",
    "mae_solar": "Solar",
    "mae_residual": "Residual",
}

st.set_page_config(page_title="German electricity pressure", layout="wide")


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def _melt_mae(df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    """Long form of a wide MAE table for multi-series plotting."""
    long = df.melt(id_col, value_vars=list(MAE_LABELS), var_name="component", value_name="mae")
    long["component"] = long["component"].map(MAE_LABELS)
    return long


def main() -> None:
    st.title("German electricity: demand, supply pressure & price")
    st.caption(
        "2019–2025 · SMARD (Bundesnetzagentur). A screening tool — findings are "
        "observational, not causal. Residual load = load − wind − solar."
    )

    if not DB_PATH.exists():
        st.error(
            f"Data not found at {DB_PATH}. Build it first (see README): "
            "download_smard → build_fact_hourly → build_forecast_hourly → build_mart."
        )
        st.stop()

    con = get_con()

    # --- filters ---------------------------------------------------------
    st.sidebar.header("Filters")
    years = st.sidebar.multiselect("Years", list(q.YEARS), default=list(q.YEARS))
    seasons = st.sidebar.multiselect("Seasons", list(q.SEASONS), default=list(q.SEASONS))
    if not years:
        years = list(q.YEARS)
    if not seasons:
        seasons = list(q.SEASONS)
    st.sidebar.caption(
        "Year/season filter the hourly views. The residual duration curve and "
        "the net-import-by-year bars are always shown per year."
    )

    tab_res, tab_price, tab_imp, tab_fc = st.tabs(
        ["Residual load", "Price by pressure", "Import reliance", "Forecast accuracy"]
    )

    # --- residual load ---------------------------------------------------
    with tab_res:
        m = q.residual_metrics(con, years, seasons).iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Peak residual (MW)", f"{int(m.peak_mw):,}")
        c2.metric("Median residual (MW)", f"{int(m.median_mw):,}")
        c3.metric("Hours residual < 0", f"{int(m.hours_below_zero):,}")

        st.subheader("Duration curve by year")
        st.caption("Residual sorted high→low; x is the share of the year's hours at or above.")
        dur = q.residual_duration(con, years)
        if not dur.empty:
            fig = px.line(
                dur, x="pct_hours", y="residual_load", color="year",
                labels={"pct_hours": "% of hours ≥", "residual_load": "Residual load (MW)"},
            )
            fig.add_hline(y=0, line_dash="dot", line_color="gray")
            st.plotly_chart(fig, width="stretch")

        st.subheader("Average residual by hour of day")
        prof = q.residual_profile_by_hour(con, years, seasons)
        fig = px.line(
            prof, x="hour_local", y="avg_residual",
            labels={"hour_local": "Hour (Berlin)", "avg_residual": "Avg residual (MW)"},
        )
        fig.add_hline(y=0, line_dash="dot", line_color="gray")
        st.plotly_chart(fig, width="stretch")

    # --- price by pressure ----------------------------------------------
    with tab_price:
        st.subheader("Day-ahead price across residual-pressure deciles")
        st.caption(
            "Decile 1 = loosest (most VRE headroom), 10 = tightest. Deciles are "
            "fixed over the whole window; filtering changes which hours fall in each."
        )
        pr = q.price_by_decile(con, years, seasons)
        if not pr.empty:
            long = pr.melt(
                "residual_decile", value_vars=["median_price", "mean_price"],
                var_name="stat", value_name="eur_mwh",
            )
            long["stat"] = long["stat"].map({"median_price": "Median", "mean_price": "Mean"})
            fig = px.bar(
                long, x="residual_decile", y="eur_mwh", color="stat", barmode="group",
                labels={"residual_decile": "Residual decile", "eur_mwh": "Price (EUR/MWh)", "stat": ""},
            )
            st.plotly_chart(fig, width="stretch")
            st.caption("Mean above median in the top decile is the price-spike tail.")
            st.dataframe(pr, width="stretch", hide_index=True)

    # --- import reliance -------------------------------------------------
    with tab_imp:
        st.subheader("Commercial net position by year")
        st.caption(
            "Commercial (market-coupled) position, not physical flow. + TWh = net "
            "importer. A net-import hour means importing was economic, not that "
            "Germany ran short."
        )
        iy = q.import_by_year(con, years)
        if not iy.empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(
                px.bar(iy, x="year", y="net_importer_days",
                       labels={"net_importer_days": "Net-importer days", "year": ""}),
                width="stretch",
            )
            fig = px.bar(iy, x="year", y="net_import_twh",
                         labels={"net_import_twh": "Net import (TWh, + = importer)", "year": ""})
            fig.add_hline(y=0, line_color="gray")
            c2.plotly_chart(fig, width="stretch")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Net-import share by hour")
            ih = q.import_share_by_hour(con, years, seasons)
            c1.plotly_chart(
                px.line(ih, x="hour_local", y="net_importer_pct",
                        labels={"hour_local": "Hour (Berlin)", "net_importer_pct": "% hours net importing"}),
                width="stretch",
            )
        with c2:
            st.subheader("Net-import share by VRE coverage")
            iv = q.import_share_by_vre_band(con, years, seasons)
            c2.plotly_chart(
                px.bar(iv, x="vre_band", y="net_importer_pct",
                       labels={"vre_band": "VRE coverage band", "net_importer_pct": "% hours net importing"}),
                width="stretch",
            )

    # --- forecast accuracy ----------------------------------------------
    with tab_fc:
        st.subheader("Day-ahead forecast accuracy")
        st.caption(
            "MAE = mean(|forecast − actual|), MW. Residual is derived "
            "(fc_load − fc_wind − fc_solar), so its error compounds the others."
        )
        ov = q.forecast_mae_overall(con, years, seasons).iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Load MAE", f"{int(ov.mae_load):,} MW", f"{ov.load_pct}% of actual")
        c2.metric("Wind MAE", f"{int(ov.mae_wind):,} MW", f"{ov.wind_pct}% of actual")
        c3.metric("Solar MAE", f"{int(ov.mae_solar):,} MW", f"{ov.solar_pct}% of actual")
        c4.metric("Residual MAE", f"{int(ov.mae_residual):,} MW", f"{ov.residual_pct}% of actual")

        st.subheader("MAE by year")
        st.caption("Solar's absolute MAE roughly doubles with the growing PV fleet, not method drift.")
        st.plotly_chart(
            px.line(_melt_mae(q.forecast_mae_by_year(con), "year"),
                    x="year", y="mae", color="component",
                    labels={"mae": "MAE (MW)", "year": "", "component": ""}),
            width="stretch",
        )

        c1, c2 = st.columns(2)
        c1.subheader("MAE by month")
        c1.plotly_chart(
            px.line(_melt_mae(q.forecast_mae_by_month(con, years), "month"),
                    x="month", y="mae", color="component",
                    labels={"mae": "MAE (MW)", "month": "", "component": ""}),
            width="stretch",
        )
        c2.subheader("MAE by hour")
        c2.plotly_chart(
            px.line(_melt_mae(q.forecast_mae_by_hour(con, years, seasons), "hour_local"),
                    x="hour_local", y="mae", color="component",
                    labels={"mae": "MAE (MW)", "hour_local": "Hour (Berlin)", "component": ""}),
            width="stretch",
        )

    st.caption("Source: Bundesnetzagentur | SMARD.de (CC BY 4.0). See findings.md and docs/.")


if __name__ == "__main__":
    main()
