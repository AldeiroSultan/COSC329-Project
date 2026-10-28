import pytest

from study_planner.inference import StudentEvidence, query
from study_planner.network import build_handcrafted_model

pytestmark = pytest.mark.skip(reason="implement in MF-00004")


def test_low_quiz_lowers_mastery():
    model = build_handcrafted_model()
    no_quiz = query(model, StudentEvidence({"C1": "medium", "C2": "medium", "C3": "medium"}, 7))
    low_quiz = query(model, StudentEvidence({"C1": "medium", "C2": "medium", "C3": "medium"}, 7, {"C1": "low"}))
    assert low_quiz.p_mastery_high["C1"] < no_quiz.p_mastery_high["C1"]
