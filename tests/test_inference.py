import pytest

from study_planner import config as cfg
from study_planner.inference import StudentEvidence, query
from study_planner.network import build_handcrafted_model


@pytest.fixture(scope="module")
def model():
    return build_handcrafted_model()


def medium(days=7, quiz=None, sleep=None):
    return StudentEvidence({"C1": "medium", "C2": "medium", "C3": "medium"}, days, quiz or {}, sleep)


def test_to_pgmpy_skips_unobserved_and_buckets_days():
    ev = StudentEvidence({"C1": "easy", "C2": "hard", "C3": "medium"}, 5, {"C1": "high", "C2": None}, None)
    assert ev.to_pgmpy() == {
        "Difficulty_C1": "easy",
        "Difficulty_C2": "hard",
        "Difficulty_C3": "medium",
        "DaysLeft": "some",
        "Quiz_C1": "high",
    }
    assert ev.days_state == "some"


def test_to_pgmpy_includes_sleep():
    assert medium(sleep="poor").to_pgmpy()[cfg.NODE_SLEEP] == "poor"


def test_difficulty_only_posterior_equals_the_cpt(model):
    post = query(model, StudentEvidence({"C1": "easy", "C2": "medium", "C3": "hard"}, 7))
    assert post.p_mastery_high == pytest.approx({"C1": 0.80, "C2": 0.55, "C3": 0.25})
    assert post.p_stress_high == pytest.approx(0.45)  # DaysLeft = some


def test_quiz_updates_mastery_by_bayes_rule(model):
    # P(M=high | easy, quiz=high) = .8*.85 / (.8*.85 + .2*.2)
    ev = StudentEvidence({"C1": "easy", "C2": "easy", "C3": "easy"}, 7, {"C1": "high"})
    assert query(model, ev).p_mastery_high["C1"] == pytest.approx(0.68 / 0.72)


def test_low_quiz_lowers_mastery(model):
    no_quiz = query(model, medium())
    low_quiz = query(model, medium(quiz={"C1": "low"}))
    high_quiz = query(model, medium(quiz={"C1": "high"}))
    assert low_quiz.p_mastery_high["C1"] < no_quiz.p_mastery_high["C1"] < high_quiz.p_mastery_high["C1"]
    # evidence about C1 does not change belief about C2
    assert low_quiz.p_mastery_high["C2"] == pytest.approx(no_quiz.p_mastery_high["C2"])


def test_poor_sleep_raises_stress(model):
    base = query(model, medium()).p_stress_high
    assert query(model, medium(sleep="poor")).p_stress_high > base > query(model, medium(sleep="good")).p_stress_high


def test_fewer_days_raises_stress_and_lowers_pass_chance(model):
    few, many = query(model, medium(days=2)), query(model, medium(days=18))
    assert few.p_stress_high > many.p_stress_high
    assert few.p_pass < many.p_pass


def test_easier_concepts_mean_higher_pass_chance(model):
    hard = query(model, StudentEvidence({"C1": "hard", "C2": "hard", "C3": "hard"}, 7))
    easy = query(model, StudentEvidence({"C1": "easy", "C2": "easy", "C3": "easy"}, 7))
    assert hard.p_pass < easy.p_pass


def test_all_posteriors_are_probabilities(model):
    post = query(model, medium(quiz={"C1": "low", "C2": "high"}, sleep="poor"))
    values = [*post.p_mastery_high.values(), post.p_stress_high, post.p_pass]
    assert all(0.0 <= v <= 1.0 for v in values)
