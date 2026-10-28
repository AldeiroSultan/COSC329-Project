import pytest

from study_planner import config as cfg
from study_planner.decision import decide
from study_planner.inference import query
from study_planner.network import build_handcrafted_model
from study_planner.scenarios import SCENARIOS

pytestmark = pytest.mark.skip(reason="implement in MF-00004")


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_scenarios_pick_expected_action(scenario):
    model = build_handcrafted_model()
    post = query(model, scenario.evidence)
    decision = decide(model, post, cfg.days_bucket(scenario.evidence.days_until_exam))
    assert decision.best.key == scenario.expected_action


def test_at_least_three_distinct_actions_across_scenarios():
    model = build_handcrafted_model()
    picked = {
        decide(model, query(model, s.evidence), cfg.days_bucket(s.evidence.days_until_exam)).best.key
        for s in SCENARIOS
    }
    assert len(picked) >= 3
