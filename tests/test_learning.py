import pandas as pd
import pytest

from study_planner import config as cfg
from study_planner.learning import laplace_cpd

pytestmark = pytest.mark.skip(reason="implement in MF-00003")


def test_laplace_unseen_state_gets_nonzero_probability():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low"] * 5, cfg.NODE_SLEEP: ["good"] * 5})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    # stress=low column: (0+1)/(5+2) poor, (5+1)/(5+2) good
    assert cpd.get_value(**{cfg.NODE_SLEEP: "poor", cfg.NODE_STRESS: "low"}) == pytest.approx(1 / 7)


def test_columns_sum_to_one():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low", "high", "high"], cfg.NODE_SLEEP: ["good", "poor", "good"]})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    assert cpd.get_values().sum(axis=0) == pytest.approx([1.0, 1.0])
