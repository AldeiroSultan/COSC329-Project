import sys

import pytest

from study_planner import cli, config as cfg
from study_planner.network import build_handcrafted_model
from study_planner.scenarios import SCENARIOS
from study_planner.sensitivity import decisions_with, format_report, run_sensitivity, settings

BASELINE = {s.name: s.expected_action for s in SCENARIOS}


@pytest.fixture(scope="module")
def model():
    return build_handcrafted_model()


def test_baseline_matches_the_expected_actions(model):
    assert decisions_with(model) == BASELINE


def test_config_is_restored_after_a_run(model):
    before = (cfg.TIME_COST_PER_HOUR, dict(cfg.UTILITY), list(cfg.ACTIONS), dict(cfg.URGENCY))
    run_sensitivity(model)
    assert (cfg.TIME_COST_PER_HOUR, dict(cfg.UTILITY), list(cfg.ACTIONS), dict(cfg.URGENCY)) == before


def test_config_is_restored_even_if_a_decision_fails(model, monkeypatch):
    monkeypatch.setattr("study_planner.sensitivity.decide", lambda *a, **k: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        decisions_with(model, {"TIME_COST_PER_HOUR": 99.0})
    assert cfg.TIME_COST_PER_HOUR == 1.0


def test_a_huge_time_cost_turns_every_plan_into_a_rest_day(model):
    assert set(decisions_with(model, {"TIME_COST_PER_HOUR": 50.0}).values()) == {"rest"}


def test_each_assumption_is_changed_in_both_directions():
    rows = settings()
    assert len(rows) == 10
    names = [assumption for assumption, _, _ in rows]
    assert all(names.count(n) == 2 for n in set(names))


def test_less_valuable_studying_never_makes_a_plan_heavier(model):
    order = {"rest": 0, "light": 1, "focused": 2, "intense": 3}
    _, rows = run_sensitivity(model)
    low = [r for r in rows if r["setting"] in ("2.0", "70", "x0.75")]
    assert any(r["changed"] for r in low)
    for row in low:
        for old, new in row["changed"].values():
            assert order[new] < order[old]


def test_advanced_student_is_robust_to_every_change(model):
    _, rows = run_sensitivity(model)
    assert all("advanced" not in row["changed"] for row in rows)


def test_report_text_and_cli(model, monkeypatch, capsys):
    text = format_report(*run_sensitivity(model))
    assert "Baseline decisions:" in text and "Which decisions change" in text and "struggling: intense -> light" in text
    monkeypatch.setattr(sys, "argv", ["study_planner", "sensitivity", "--handcrafted"])
    cli.main()
    assert "Decisions changed in" in capsys.readouterr().out
