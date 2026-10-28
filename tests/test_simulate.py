import pytest

from study_planner import config as cfg
from study_planner.simulate_data import simulate_students

pytestmark = pytest.mark.skip(reason="implement in MF-00002")


def test_shape_and_reproducible():
    a = simulate_students(500, seed=1)
    b = simulate_students(500, seed=1)
    assert len(a) == 500
    assert a.equals(b)


def test_states_are_valid():
    df = simulate_students(500)
    assert set(df[cfg.NODE_STRESS]) <= set(cfg.STRESS_STATES)
    assert set(df[cfg.NODE_DAYS]) <= set(cfg.DAYS_STATES)
