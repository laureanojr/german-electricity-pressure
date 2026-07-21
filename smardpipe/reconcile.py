"""Reconcile the completed 2025 year against Bundesnetzagentur headline figures.

The project's "sanity check with teeth": independent aggregates derived from
fact_hourly must land near the officially published 2025 numbers.

Official definition (Bundesnetzagentur press release, 2025 electricity market
data, 2026-01-05): "actual generation" is **net electricity generation** — the
electricity fed into the general supply network less power plants' own
consumption. It excludes the Deutsche Bahn network, industrial and closed
distribution networks, and self-consumed household PV. That is exactly the sum
of all realised-generation categories on SMARD (our 12 columns, pumped storage
included). See docs/methodology.md for the per-source comparison and the
explained residual.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# All realised-generation categories = net electricity generation (see above).
GENERATION_COLUMNS = (
    "wind_onshore", "wind_offshore", "solar",
    "lignite", "hard_coal", "gas",
    "biomass", "hydro", "nuclear", "pumped_storage_gen",
    "other_conventional", "other_renewable",
)

OFFICIAL_SOURCE = (
    "Bundesnetzagentur | SMARD.de — 2025 electricity market data "
    "(press release 2026-01-05)"
)

# Columns the reconciliation actually reads. Used to carve the small CI fixture
# (tests/fixtures/fact_2025_reconcile.parquet) so the with-teeth gate can run in
# CI without the full, gitignored fact_hourly.
RECONCILE_COLUMNS = GENERATION_COLUMNS + ("day_ahead_price", "net_import", "year")


@dataclass(frozen=True)
class Metric:
    """One reconciled quantity with either a relative or absolute tolerance."""

    key: str
    official: float
    label: str
    rel_tol: float | None = None
    abs_tol: float | None = None

    def diff(self, got: float) -> float:
        if self.rel_tol is not None:
            return abs(got - self.official) / self.official
        return abs(got - self.official)

    def tol(self) -> float:
        return self.rel_tol if self.rel_tol is not None else self.abs_tol

    def kind(self) -> str:
        return "rel" if self.rel_tol is not None else "abs"

    def passes(self, got: float) -> bool:
        return self.diff(got) <= self.tol()


# Figures quoted verbatim from the press release. Generation to 0.1 TWh; price
# exact; net imports 0.1 TWh; negative-price hours exact.
OFFICIAL_2025 = (
    Metric("total_generation_twh", 437.6,
           "Net electricity generation (TWh)", rel_tol=0.010),
    Metric("avg_day_ahead_price_eur_mwh", 89.32,
           "Avg day-ahead price (EUR/MWh)", rel_tol=0.010),
    Metric("net_imports_twh", 21.9,
           "Commercial net imports (TWh)", rel_tol=0.050),
    Metric("negative_price_hours", 573,
           "Hours with negative price", abs_tol=15),
)


def compute_2025_summary(fact: pd.DataFrame) -> dict:
    """Compute the reconciliation aggregates for calendar year 2025."""
    f = fact[fact["year"] == 2025]
    if f.empty:
        raise ValueError("no 2025 rows in fact_hourly")
    gen_twh = float(f[list(GENERATION_COLUMNS)].sum(numeric_only=True).sum()) / 1e6
    return {
        "total_generation_twh": gen_twh,
        "avg_day_ahead_price_eur_mwh": float(f["day_ahead_price"].mean()),
        "net_imports_twh": float(f["net_import"].sum()) / 1e6,
        "negative_price_hours": int((f["day_ahead_price"] < 0).sum()),
        "hours": int(len(f)),
    }


def reconcile(fact: pd.DataFrame, metrics=OFFICIAL_2025) -> pd.DataFrame:
    """Per-metric comparison table with a pass/fail column."""
    summary = compute_2025_summary(fact)
    rows = []
    for m in metrics:
        got = summary[m.key]
        rows.append({
            "metric": m.label,
            "computed": round(got, 4),
            "official": m.official,
            "diff": round(m.diff(got), 4),
            "tol": m.tol(),
            "kind": m.kind(),
            "pass": bool(m.passes(got)),
        })
    return pd.DataFrame(rows)


def assert_reconciled(fact: pd.DataFrame, metrics=OFFICIAL_2025) -> pd.DataFrame:
    """Raise if any metric is outside tolerance; else return the report."""
    report = reconcile(fact, metrics)
    failed = report[~report["pass"]]
    if not failed.empty:
        lines = [
            f"  {r.metric}: computed={r.computed}, official={r.official}, "
            f"diff={r.diff} > tol={r.tol} ({r.kind})"
            for r in failed.itertuples()
        ]
        raise AssertionError(
            "2025 reconciliation failed:\n" + "\n".join(lines)
        )
    return report
