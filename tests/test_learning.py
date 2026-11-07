import json

import numpy as np
import pandas as pd
import pytest

from study_planner import config as cfg
from study_planner.learning import (
    build_learned_model,
    compare_cpds,
    cpd_as_dict,
    crosscheck_with_pgmpy,
    laplace_cpd,
    learn_cpds,
    learned_variables,
    parents_of,
    save_cpds,
)
from study_planner.network import handcrafted_cpds
from study_planner.simulate_data import simulate_students, write_csv


@pytest.fixture(scope="module")
def df():
    return simulate_students()


@pytest.fixture(scope="module")
def csv_path(df, tmp_path_factory):
    return write_csv(df, tmp_path_factory.mktemp("data") / "students.csv")


def test_laplace_unseen_state_gets_nonzero_probability():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low"] * 5, cfg.NODE_SLEEP: ["good"] * 5})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    # stress=low column: (0+1)/(5+2) poor, (5+1)/(5+2) good
    assert cpd.get_value(**{cfg.NODE_SLEEP: "poor", cfg.NODE_STRESS: "low"}) == pytest.approx(1 / 7)
    assert cpd.get_value(**{cfg.NODE_SLEEP: "good", cfg.NODE_STRESS: "low"}) == pytest.approx(6 / 7)


def test_columns_sum_to_one():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low", "high", "high"], cfg.NODE_SLEEP: ["good", "poor", "good"]})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    assert cpd.get_values().sum(axis=0) == pytest.approx([1.0, 1.0])


def test_unseen_parent_configuration_is_uniform():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low"] * 4, cfg.NODE_SLEEP: ["good"] * 4})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    assert cpd.get_value(**{cfg.NODE_SLEEP: "poor", cfg.NODE_STRESS: "high"}) == pytest.approx(0.5)


def test_alpha_zero_is_maximum_likelihood():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low"] * 4, cfg.NODE_SLEEP: ["good", "good", "good", "poor"]})
    cpd = laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS], alpha=0)
    assert cpd.get_value(**{cfg.NODE_SLEEP: "poor", cfg.NODE_STRESS: "low"}) == pytest.approx(0.25)


def test_unknown_state_is_rejected():
    df = pd.DataFrame({cfg.NODE_STRESS: ["low", "medium"], cfg.NODE_SLEEP: ["good", "poor"]})
    with pytest.raises(ValueError, match="medium"):
        laplace_cpd(df, cfg.NODE_SLEEP, [cfg.NODE_STRESS])


def test_parents_follow_network_structure():
    assert parents_of(cfg.NODE_MASTERY["C2"]) == [cfg.NODE_DIFFICULTY["C2"]]
    assert parents_of(cfg.NODE_STRESS) == [cfg.NODE_DAYS]
    assert parents_of(cfg.NODE_EXAM) == [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS] + [cfg.NODE_STRESS]


def test_learns_nine_cpts_covering_four_plus_variables(csv_path):
    cpds = learn_cpds(csv_path)
    assert {cpd.variable for cpd in cpds} == set(learned_variables())
    assert len(cpds) == 9
    for cpd in cpds:
        assert np.allclose(cpd.get_values().sum(axis=0), 1.0)
        assert (cpd.get_values() > 0).all()  # smoothing: nothing is ever exactly 0


def test_learned_values_are_close_to_the_generating_functions(csv_path):
    cpds = {cpd.variable: cpd for cpd in learn_cpds(csv_path)}
    mastery = cpds[cfg.NODE_MASTERY["C1"]]
    easy = mastery.get_value(**{cfg.NODE_MASTERY["C1"]: "high", cfg.NODE_DIFFICULTY["C1"]: "easy"})
    hard = mastery.get_value(**{cfg.NODE_MASTERY["C1"]: "high", cfg.NODE_DIFFICULTY["C1"]: "hard"})
    assert easy == pytest.approx(0.80, abs=0.03)  # sigmoid(1.4)
    assert hard == pytest.approx(0.23, abs=0.04)  # sigmoid(-1.2)

    quiz = cpds[cfg.NODE_QUIZ["C2"]]
    assert quiz.get_value(**{cfg.NODE_QUIZ["C2"]: "high", cfg.NODE_MASTERY["C2"]: "high"}) == pytest.approx(0.85, abs=0.03)

    exam = cpds[cfg.NODE_EXAM]
    all_high = {cfg.NODE_MASTERY[c]: "high" for c in cfg.CONCEPTS}
    assert exam.get_value(**{cfg.NODE_EXAM: "pass", **all_high, cfg.NODE_STRESS: "low"}) == pytest.approx(0.93, abs=0.04)


@pytest.mark.parametrize("node", learned_variables())
def test_matches_pgmpy_k2_estimator(df, node):
    assert crosscheck_with_pgmpy(df, node) < 1e-9


def test_learned_model_is_valid_and_keeps_handcrafted_root_priors(csv_path):
    model = build_learned_model(csv_path)
    assert model.check_model()
    assert len(model.get_cpds()) == 13
    hand = {cpd.variable: cpd for cpd in handcrafted_cpds()}
    for root in [cfg.NODE_DAYS, *cfg.NODE_DIFFICULTY.values()]:
        assert np.allclose(model.get_cpds(root).get_values(), hand[root].get_values())


def test_compare_cpds_covers_every_cell(csv_path):
    table = compare_cpds(learn_cpds(csv_path))
    # 9 CPTs: 3x(3 configs x 2) + 3x(2 x 2) + (3 x 2) + (2 x 2) + (16 x 2) = 72 cells
    assert len(table) == 72
    assert {"cpt", "parents", "state", "handcrafted", "learned", "abs_diff"} <= set(table.columns)
    some = table[(table.cpt == cfg.NODE_STRESS) & (table.parents == "DaysLeft=some") & (table.state == "high")]
    assert some["handcrafted"].item() == pytest.approx(0.45)
    assert some["learned"].item() > 0.5  # the data corrects the hand-crafted guess


def test_save_cpds_json(csv_path, tmp_path):
    path = save_cpds(learn_cpds(csv_path), tmp_path / "out" / "learned.json")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert set(saved) == set(learned_variables())
    exam = saved[cfg.NODE_EXAM]
    assert exam["parents"] == parents_of(cfg.NODE_EXAM)
    assert exam["states"] == cfg.EXAM_STATES
    assert len(exam["values"]) == 2 and len(exam["values"][0]) == 16
    assert np.allclose(np.array(exam["values"]).sum(axis=0), 1.0)


def test_cpd_as_dict_sums_to_one_per_parent_configuration(csv_path):
    cpd = learn_cpds(csv_path)[-1]  # ExamSuccess
    table = cpd_as_dict(cpd)
    assert len(table) == 32
    for config in {key[1] for key in table}:
        assert sum(p for (_, c), p in table.items() if c == config) == pytest.approx(1.0)
