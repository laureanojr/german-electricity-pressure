"""Guard the confirmed SMARD filter IDs against accidental edits.

These are the [CFG]-confirmed data_ids from docs/data_dictionary.md. If someone
changes one, this test should fail loudly.
"""

from smardpipe import series as S


def test_key_generation_ids():
    by_key = {s.key: s.data_id for s in S.GENERATION}
    assert by_key["solar"] == 4068
    assert by_key["hard_coal"] == 4069
    assert by_key["gas"] == 4071
    assert by_key["lignite"] == 1223
    assert by_key["wind_onshore"] == 4067
    assert by_key["wind_offshore"] == 1225


def test_load_price_and_commercial_ids():
    assert S.LOAD.data_id == 410
    assert S.PRICE.data_id == 4169
    assert S.PRICE.region == "DE-LU"
    assert S.COMMERCIAL_NETEXPORT_OLD.data_id == 661
    assert S.COMMERCIAL_NETEXPORT_NEW.data_id == 4629


def test_aggregation_rules():
    # energy sums, price means -- the units discipline lives here.
    assert S.LOAD.agg == "sum"
    assert all(s.agg == "sum" for s in S.GENERATION)
    assert S.PRICE.agg == "mean"


def test_residual_definition_is_wind_and_solar_only():
    assert S.VRE_FOR_RESIDUAL == ("wind_onshore", "wind_offshore", "solar")
