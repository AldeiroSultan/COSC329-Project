import pytest

from study_planner import config as cfg
from study_planner.decision import (
    apply_action,
    decide,
    expected_utility,
    utility,
    weakest_concept,
)
from study_planner.inference import Posteriors, StudentEvidence, query
from study_planner.learning import build_learned_model
from study_planner.network import build_handcrafted_model
from study_planner.scenarios import SCENARIOS
from study_planner.simulate_data import simulate_students, write_csv

ACTIONS = {a.key: a for a in cfg.ACTIONS}


@pytest.fixture(scope="module")
def handcrafted():
    return build_handcrafted_model()


@pytest.fixture(scope="module")
def learned(tmp_path_factory):
    path = write_csv(simulate_students(), tmp_path_factory.mktemp("data") / "students.csv")
    return build_learned_model(path)


@pytest.fixture(params=["handcrafted", "learned"])
def model(request, handcrafted, learned):
    return handcrafted if request.param == "handcrafted" else learned


def decide_for(model, evidence):
    return decide(model, query(model, evidence), evidence.days_state)


def post(m1, m2, m3, stress):
    return Posteriors({"C1": m1, "C2": m2, "C3": m3}, stress, 0.5)


# ------------------------------------------------------------------ utility & actions
def test_there_are_at_least_three_actions_including_a_rest_day():
    assert len(cfg.ACTIONS) >= 3
    assert {"intense", "light", "rest"} <= set(ACTIONS)
    assert ACTIONS["intense"].hours == 5.0 and ACTIONS["light"].hours == 1.0 and ACTIONS["rest"].hours == 0.0


def test_utility_prefers_passing_and_low_stress():
    assert utility("pass", "low") > utility("pass", "high") > utility("fail", "low") > utility("fail", "high")


def test_weakest_concept_and_tie_break():
    assert weakest_concept(post(0.9, 0.2, 0.5, 0.5)) == "C2"
    assert weakest_concept(post(0.4, 0.4, 0.4, 0.5)) == "C1"


def test_rest_only_lowers_stress():
    mastery, stress = apply_action(post(0.3, 0.5, 0.7, 0.5), ACTIONS["rest"], "few")
    assert mastery == {"C1": 0.3, "C2": 0.5, "C3": 0.7}
    assert stress == pytest.approx(0.5 + ACTIONS["rest"].stress_delta)


def test_intense_boosts_every_concept_scaled_by_urgency():
    boost = ACTIONS["intense"].mastery_boost
    mastery, stress = apply_action(post(0.2, 0.2, 0.2, 0.5), ACTIONS["intense"], "few")
    assert mastery["C1"] == pytest.approx(0.2 + boost * 0.8)
    mastery_early, _ = apply_action(post(0.2, 0.2, 0.2, 0.5), ACTIONS["intense"], "many")
    assert 0.2 < mastery_early["C1"] < mastery["C1"]  # same session matters less far from the exam
    assert stress > 0.5


def test_focused_only_boosts_the_weakest_concept():
    mastery, _ = apply_action(post(0.8, 0.8, 0.1, 0.5), ACTIONS["focused"], "few")
    assert mastery["C1"] == 0.8 and mastery["C2"] == 0.8
    assert mastery["C3"] > 0.1


def test_stress_is_clipped_to_a_probability():
    _, high = apply_action(post(0.5, 0.5, 0.5, 0.95), ACTIONS["intense"], "few")
    _, low = apply_action(post(0.5, 0.5, 0.5, 0.01), ACTIONS["rest"], "few")
    assert high == 1.0 and low == 0.0


# ------------------------------------------------------------------ expected utility
def test_expected_utility_by_hand(handcrafted):
    # Certain mastery of everything, certainly calm: P(pass | 3 mastered, low) = .95
    perfect = post(1.0, 1.0, 1.0, 0.0)
    by_hand = 0.95 * utility("pass", "low") + 0.05 * utility("fail", "low")
    assert expected_utility(handcrafted, perfect, ACTIONS["rest"], "few") == pytest.approx(by_hand)
    # light adds a 1 hour time cost and cannot improve certainty
    assert expected_utility(handcrafted, perfect, ACTIONS["light"], "few") == pytest.approx(
        by_hand - cfg.TIME_COST_PER_HOUR * ACTIONS["light"].hours
    )


def test_time_cost_is_charged_per_hour(handcrafted, monkeypatch):
    perfect = post(1.0, 1.0, 1.0, 0.0)
    monkeypatch.setattr(cfg, "TIME_COST_PER_HOUR", 0.0)
    free = {k: expected_utility(handcrafted, perfect, a, "many") for k, a in ACTIONS.items()}
    monkeypatch.setattr(cfg, "TIME_COST_PER_HOUR", 2.0)
    paid = {k: expected_utility(handcrafted, perfect, a, "many") for k, a in ACTIONS.items()}
    for key, action in ACTIONS.items():
        assert free[key] - paid[key] == pytest.approx(2.0 * action.hours)


def test_decide_returns_the_argmax_and_all_actions(handcrafted):
    decision = decide(handcrafted, post(0.1, 0.1, 0.1, 0.8), "few")
    assert set(decision.expected_utility) == set(ACTIONS)
    assert decision.expected_utility[decision.best.key] == max(decision.expected_utility.values())
    assert decision.target_concept == "C1"


def test_expected_utility_matches_hand_calculation_in_model_md(handcrafted):
    struggling = SCENARIOS[0]
    eu = decide_for(handcrafted, struggling.evidence).expected_utility
    assert eu["intense"] == pytest.approx(22.4, abs=0.05)
    assert eu["light"] == pytest.approx(21.8, abs=0.05)
    assert eu["rest"] == pytest.approx(11.7, abs=0.05)


# ------------------------------------------------------------------ scenarios (docs/MODEL.md §6)
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_scenarios_pick_expected_action(model, scenario):
    assert decide_for(model, scenario.evidence).best.key == scenario.expected_action


def test_at_least_three_distinct_actions_across_scenarios(model):
    picked = {decide_for(model, s.evidence).best.key for s in SCENARIOS}
    assert len(picked) >= 3


def test_struggling_student_studies_more_than_advanced_student(model):
    struggling = decide_for(model, SCENARIOS[0].evidence)
    advanced = decide_for(model, SCENARIOS[1].evidence)
    assert struggling.best.hours > advanced.best.hours


def test_same_student_is_pushed_harder_as_the_exam_gets_closer(model):
    def gain(days):
        ev = StudentEvidence({"C1": "hard", "C2": "hard", "C3": "hard"}, days, {"C1": "low", "C2": "low", "C3": "low"})
        eu = decide_for(model, ev).expected_utility
        return eu["intense"] - eu["rest"]

    assert gain(2) > gain(8) > gain(18)


def test_one_weak_concept_is_targeted(model):
    decision = decide_for(model, SCENARIOS[2].evidence)  # C3 is the hard one
    assert decision.best.key == "focused"
    assert decision.target_concept == "C3"
