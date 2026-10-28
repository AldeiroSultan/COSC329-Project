import pytest

from study_planner import config as cfg
from study_planner.network import build_handcrafted_model, network_edges

pytestmark = pytest.mark.skip(reason="implement in MF-00001")


def test_structure_has_13_nodes():
    nodes = {n for edge in network_edges() for n in edge}
    assert len(nodes) == 13


def test_model_is_valid():
    assert build_handcrafted_model().check_model()


def test_exam_cpd_matches_handcrafted_table():
    cpd = build_handcrafted_model().get_cpds(cfg.NODE_EXAM)
    # all mastered + low stress -> 0.95
    values = cpd.get_value(**{cfg.NODE_EXAM: "pass", **{cfg.NODE_MASTERY[c]: "high" for c in cfg.CONCEPTS},
                              cfg.NODE_STRESS: "low"})
    assert values == pytest.approx(0.95)
