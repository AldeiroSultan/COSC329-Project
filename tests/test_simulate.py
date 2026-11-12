import pandas as pd
import pytest

from study_planner import config as cfg
from study_planner.network import state_names
from study_planner.simulate_data import (
    COLUMNS,
    learned_cpt_parents,
    parent_config_counts,
    simulate_students,
    write_csv,
)


@pytest.fixture(scope="module")
def df():
    return simulate_students()


def test_shape_and_reproducible():
    a = simulate_students(500, seed=1)
    b = simulate_students(500, seed=1)
    assert len(a) == 500
    assert a.equals(b)
    assert not a.equals(simulate_students(500, seed=2))


def test_default_size_and_columns(df):
    assert len(df) == cfg.N_STUDENTS
    assert list(df.columns) == COLUMNS
    assert df["student_id"].is_unique


def test_states_are_valid(df):
    for node, states in state_names().items():
        assert set(df[node]) <= set(states), node
    assert df["days_until_exam"].between(1, 21).all()


def test_days_bucket_matches_raw_days(df):
    expected = df["days_until_exam"].map(cfg.days_bucket)
    assert (df[cfg.NODE_DAYS] == expected).all()


def test_frequencies_follow_generative_functions(df):
    hard = df[df[cfg.NODE_DIFFICULTY["C1"]] == "hard"]
    easy = df[df[cfg.NODE_DIFFICULTY["C1"]] == "easy"]
    p_hard = (hard[cfg.NODE_MASTERY["C1"]] == "high").mean()
    p_easy = (easy[cfg.NODE_MASTERY["C1"]] == "high").mean()
    assert p_hard == pytest.approx(0.23, abs=0.05)
    assert p_easy == pytest.approx(0.80, abs=0.05)

    few = df[df[cfg.NODE_DAYS] == "few"]
    many = df[df[cfg.NODE_DAYS] == "many"]
    assert (few[cfg.NODE_STRESS] == "high").mean() > (many[cfg.NODE_STRESS] == "high").mean() + 0.3

    stressed = df[df[cfg.NODE_STRESS] == "high"]
    calm = df[df[cfg.NODE_STRESS] == "low"]
    assert (stressed[cfg.NODE_SLEEP] == "poor").mean() == pytest.approx(0.65, abs=0.05)
    assert (calm[cfg.NODE_SLEEP] == "poor").mean() == pytest.approx(0.25, abs=0.05)


def test_exam_success_rises_with_mastery_and_falls_with_stress(df):
    k = sum((df[cfg.NODE_MASTERY[c]] == "high").astype(int) for c in cfg.CONCEPTS)
    passed = df[cfg.NODE_EXAM] == "pass"
    rates = passed.groupby(k).mean()
    assert rates.is_monotonic_increasing
    for level in range(4):
        low = passed[(k == level) & (df[cfg.NODE_STRESS] == "low")].mean()
        high = passed[(k == level) & (df[cfg.NODE_STRESS] == "high")].mean()
        assert low > high


def test_every_parent_configuration_has_enough_rows(df):
    counts = parent_config_counts(df)
    assert set(counts) == set(learned_cpt_parents())
    for label, series in counts.items():
        assert series.sum() == len(df), label
        assert (series > 10).all(), label


def test_parent_config_counts_lists_unseen_configurations(df):
    no_hard = df[df[cfg.NODE_DIFFICULTY["C1"]] != "hard"]
    label = f"{cfg.NODE_MASTERY['C1']} | {cfg.NODE_DIFFICULTY['C1']}"
    series = parent_config_counts(no_hard)[label]
    assert series.loc["hard"] == 0
    assert series.loc["easy"] > 0


def test_write_csv_round_trip(tmp_path):
    df = simulate_students(100)
    path = write_csv(df, tmp_path / "nested" / "students.csv")
    assert pd.read_csv(path).equals(df)


def test_committed_csv_matches_documented_schema_and_seed(df):
    submitted = pd.read_csv(cfg.STUDENTS_CSV)
    assert list(submitted.columns) == COLUMNS
    assert len(submitted) == cfg.N_STUDENTS
    assert not submitted.isna().any().any()
    assert submitted["student_id"].tolist() == list(range(1, cfg.N_STUDENTS + 1))
    for node, states in state_names().items():
        assert set(submitted[node]) <= set(states), node
    days = submitted["days_until_exam"]
    assert pd.api.types.is_integer_dtype(days)
    assert days.between(1, 21).all()
    # Independent boundary check against DATA.md, rather than calling days_bucket.
    expected = days.map(lambda day: "few" if day <= 3 else "some" if day <= 10 else "many")
    assert submitted[cfg.NODE_DAYS].equals(expected.rename(cfg.NODE_DAYS))
    pd.testing.assert_frame_equal(submitted, df)
