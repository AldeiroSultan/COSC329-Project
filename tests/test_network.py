import numpy as np
import pytest

from study_planner import config as cfg
from study_planner.network import build_handcrafted_model, network_edges


@pytest.fixture(scope="module")
def model():
    return build_handcrafted_model()


def test_structure_has_13_nodes():
    nodes = {n for edge in network_edges() for n in edge}
    assert len(nodes) == 13


def test_model_is_valid(model):
    assert model.check_model()


def test_every_cpd_column_sums_to_one(model):
    for cpd in model.get_cpds():
        values = cpd.get_values()
        assert np.allclose(values.sum(axis=0), 1.0), cpd.variable


def test_exam_cpd_matches_handcrafted_table(model):
    cpd = model.get_cpds(cfg.NODE_EXAM)
    all_high = {cfg.NODE_MASTERY[c]: "high" for c in cfg.CONCEPTS}
    assert cpd.get_value(**{cfg.NODE_EXAM: "pass", **all_high, cfg.NODE_STRESS: "low"}) == pytest.approx(0.95)

    one_high = {cfg.NODE_MASTERY["C1"]: "low", cfg.NODE_MASTERY["C2"]: "high", cfg.NODE_MASTERY["C3"]: "low"}
    assert cpd.get_value(**{cfg.NODE_EXAM: "pass", **one_high, cfg.NODE_STRESS: "high"}) == pytest.approx(0.25)


def test_mastery_and_sleep_cpds(model):
    mastery = model.get_cpds(cfg.NODE_MASTERY["C1"])
    assert mastery.get_value(**{cfg.NODE_MASTERY["C1"]: "high", cfg.NODE_DIFFICULTY["C1"]: "hard"}) == pytest.approx(0.25)

    sleep = model.get_cpds(cfg.NODE_SLEEP)
    assert sleep.get_value(**{cfg.NODE_SLEEP: "poor", cfg.NODE_STRESS: "high"}) == pytest.approx(0.65)
