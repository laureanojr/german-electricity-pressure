"""Reconciliation tests: 2025 filtering, aggregation, tolerance logic."""

import numpy as np
import pandas as pd
import pytest

from smardpipe import reconcile as R


def _fact():
    # One 2025 row: each of 12 generation cols = 1e6 MWh -> 12 TWh total.
    # price = 50, net_import = 2e6 MWh -> 2 TWh. Plus a 2024 row that must be
    # excluded (huge values that would break totals if counted).
    gen = {c: [1e6, 9e9] for c in R.GENERATION_COLUMNS}
    return pd.DataFrame({
        **gen,
        "day_ahead_price": [50.0, 999.0],
        "net_import": [2e6, 9e9],
        "year": [2025, 2024],
    })


def _metrics(**over):
    base = {
        "total_generation_twh": 12.0,
        "avg_day_ahead_price_eur_mwh": 50.0,
        "net_imports_twh": 2.0,
        "negative_price_hours": 0,
    }
    base.update(over)
    return (
        R.Metric("total_generation_twh", base["total_generation_twh"],
                 "gen", rel_tol=0.01),
        R.Metric("avg_day_ahead_price_eur_mwh",
                 base["avg_day_ahead_price_eur_mwh"], "price", rel_tol=0.01),
        R.Metric("net_imports_twh", base["net_imports_twh"],
                 "imports", rel_tol=0.05),
        R.Metric("negative_price_hours", base["negative_price_hours"],
                 "neg", abs_tol=1),
    )


def test_summary_uses_only_2025_and_aggregates_correctly():
    s = R.compute_2025_summary(_fact())
    assert s["hours"] == 1
    assert s["total_generation_twh"] == 12.0
    assert s["avg_day_ahead_price_eur_mwh"] == 50.0
    assert s["net_imports_twh"] == 2.0
    assert s["negative_price_hours"] == 0


def test_reconcile_passes_within_tolerance():
    report = R.reconcile(_fact(), _metrics())
    assert report["pass"].all()


def test_assert_reconciled_raises_when_generation_off():
    with pytest.raises(AssertionError, match="gen"):
        R.assert_reconciled(_fact(), _metrics(total_generation_twh=20.0))


def test_absolute_tolerance_metric_can_fail():
    # official negative hours = 100, abs_tol = 1, computed = 0 -> fail
    with pytest.raises(AssertionError, match="neg"):
        R.assert_reconciled(_fact(), _metrics(negative_price_hours=100))


def test_nuclear_nan_does_not_break_sum():
    df = _fact()
    df.loc[0, "nuclear"] = np.nan  # phased-out year: NaN, not 0
    s = R.compute_2025_summary(df)
    assert s["total_generation_twh"] == 11.0  # 11 cols * 1e6 MWh
