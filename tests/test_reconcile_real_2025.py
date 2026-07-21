"""With-teeth CI gate: the real computed 2025 numbers must match Bundesnetzagentur.

test_reconcile.py exercises the filtering / aggregation / tolerance *logic* on
synthetic rows. This runs the actual aggregation on a committed slice of real
2025 fact_hourly and asserts it lands within tolerance of the official 2025
figures. It's the "sanity check with teeth" from docs/methodology.md — now
enforced on every push instead of only when reconcile_2025.py is run locally
against gitignored data.

The fixture holds only the reconcile columns for calendar 2025 (8760 UTC hours),
~350 KB. Regenerate it from a built pipeline with:

    python scripts/reconcile_2025.py --emit-fixture tests/fixtures/fact_2025_reconcile.parquet

Fixture data: Bundesnetzagentur | SMARD.de (CC BY 4.0).
"""

from pathlib import Path

import pandas as pd

from smardpipe import reconcile as R

FIXTURE = Path(__file__).parent / "fixtures" / "fact_2025_reconcile.parquet"


def test_real_2025_reconciles_against_official():
    # assert_reconciled raises if any of the four official metrics drifts out of
    # tolerance; a passing report here is the gate.
    fact = pd.read_parquet(FIXTURE)
    report = R.assert_reconciled(fact)
    assert report["pass"].all()


def test_fixture_is_a_full_completed_year():
    # Guards against a truncated re-emit silently weakening the gate.
    fact = pd.read_parquet(FIXTURE)
    assert (fact["year"] == 2025).all()
    assert len(fact) == 8760  # 365 days x 24 UTC hours
