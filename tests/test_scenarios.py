import copy
import sys
from datetime import date, datetime, timedelta

import pytest

from study_planner import cli, config as cfg
from study_planner.calendar_api import IcsCalendarClient, InMemoryCalendarClient
from study_planner.demo import run_demo
from study_planner.network import build_handcrafted_model
from study_planner.scenarios import SCENARIOS, get_model, simulate_two_weeks

TODAY = date(2026, 11, 9)
BY_NAME = {s.name: s for s in SCENARIOS}


@pytest.fixture(scope="module")
def model():
    return build_handcrafted_model()


def run(name, model, **kwargs):
    return simulate_two_weeks(BY_NAME[name], model, today=TODAY, **kwargs)


# ------------------------------------------------------------------ scenarios
def test_at_least_four_distinct_students():
    assert len(SCENARIOS) >= 4
    assert len({s.name for s in SCENARIOS}) == len(SCENARIOS)
    assert len({s.expected_action for s in SCENARIOS}) >= 3


def test_get_model_prefers_learned_and_falls_back(monkeypatch, tmp_path):
    learned = get_model()
    assert learned.get_cpds(cfg.NODE_STRESS).get_value(Stress="high", DaysLeft="some") == pytest.approx(0.57, abs=0.01)
    hand = get_model(handcrafted=True)
    assert hand.get_cpds(cfg.NODE_STRESS).get_value(Stress="high", DaysLeft="some") == pytest.approx(0.45)
    monkeypatch.setattr(cfg, "STUDENTS_CSV", tmp_path / "missing.csv")
    assert get_model().get_cpds(cfg.NODE_STRESS).get_value(Stress="high", DaysLeft="some") == pytest.approx(0.45)


# ------------------------------------------------------------------ 14-day simulation
def test_two_week_run_counts_down_one_row_per_day(model):
    rows = run("struggling", model)
    assert [r["day"] for r in rows] == list(range(1, 15))
    assert [r["days_left"] for r in rows] == list(range(14, 0, -1))
    assert rows[0]["date"] == TODAY and rows[-1]["date"] == TODAY + timedelta(days=13)
    assert {"day", "days_left", "action", "eu", "p_pass"} <= set(rows[0])
    assert len(run("struggling", model, start_days=7)) == 7


def test_two_week_run_is_deterministic_and_does_not_change_the_scenario(model):
    before = copy.deepcopy(BY_NAME["struggling"].evidence)
    assert run("struggling", model) == run("struggling", model)
    assert BY_NAME["struggling"].evidence == before


def test_struggling_student_studies_and_advanced_student_rests(model):
    struggling, advanced = run("struggling", model), run("advanced", model)
    assert sum(r["hours"] for r in struggling) > sum(r["hours"] for r in advanced)
    assert all(r["action"] == "rest" for r in advanced)
    assert all(r["hours"] > 0 for r in struggling)


def test_studying_raises_true_mastery_and_flips_the_quiz(model):
    rows = run("struggling", model)
    first = list(rows[0]["mastery"].values())
    last = list(rows[-1]["mastery"].values())
    assert all(b > a for a, b in zip(first, last))
    assert set(rows[0]["quiz"].values()) == {"low"} and set(rows[-1]["quiz"].values()) == {"high"}
    flip = next(i for i, r in enumerate(rows) if set(r["quiz"].values()) == {"high"})
    # new evidence changes the next decision: expected utility and pass chance jump
    assert rows[flip]["p_pass"] > rows[flip - 1]["p_pass"] + 0.3
    assert rows[flip]["eu"] > rows[flip - 1]["eu"] + 20


def test_plan_changes_as_the_exam_approaches(model):
    actions = [r["action"] for r in run("burnt_out", model)]
    assert actions[0] == "rest" and actions[-1] == "light"  # eases back in once the exam is close
    assert len(set(actions)) >= 2


def test_only_quizzed_concepts_are_tracked(model):
    assert set(run("one_weak_spot", model)[0]["quiz"]) == {"C3"}
    assert run("average_early", model)[0]["quiz"] == {}


def test_two_week_run_writes_the_calendar(model):
    calendar = InMemoryCalendarClient()
    rows = run("struggling", model, calendar=calendar)
    sessions = [e for e in calendar.events if e.is_planner_event]
    assert len(sessions) == sum(1 for r in rows if r["hours"] > 0)
    assert sorted(e.start.date() for e in sessions) == [r["date"] for r in rows]


def test_rest_days_leave_no_session(model):
    calendar = InMemoryCalendarClient()
    run("advanced", model, calendar=calendar)
    assert calendar.events == []


# ------------------------------------------------------------------ demo command
def test_demo_prints_the_story_and_writes_calendars(model, tmp_path):
    lines = []
    summary = run_demo(model, TODAY, tmp_path, out=lines.append)
    text = "\n".join(lines)

    assert [row["match"] for row in summary] == [True] * len(SCENARIOS)
    assert len({row["action"] for row in summary}) >= 3
    for s in SCENARIOS:
        assert f"=== {s.name} ===" in text
        assert (tmp_path / f"{s.name}.ics").exists()
    assert "Expected utility:" in text and "<-- best" in text and "Decision:" in text
    assert "14-day run: struggling" in text and "14-day run: advanced" in text

    struggling = IcsCalendarClient.load(tmp_path / "struggling.ics")
    (session,) = struggling.events
    assert session.summary.startswith(cfg.EVENT_TAG) and (session.end - session.start).seconds == 5 * 3600
    assert IcsCalendarClient.load(tmp_path / "advanced.ics").events == []
    assert len(IcsCalendarClient.load(tmp_path / "two_week_struggling.ics").events) == 14


def test_demo_only_runs_the_chosen_student(model, tmp_path):
    lines = []
    run_demo(model, TODAY, tmp_path, only="advanced", out=lines.append)
    assert (tmp_path / "advanced.ics").exists() and not (tmp_path / "struggling.ics").exists()
    assert "14-day run: advanced" in "\n".join(lines)


def test_demo_google_writes_one_scenario_to_the_google_client(model, tmp_path, monkeypatch):
    fake = InMemoryCalendarClient()
    monkeypatch.setattr("study_planner.calendar_api.google_calendar.GoogleCalendarClient", lambda: fake)
    run_demo(model, TODAY, tmp_path, only="struggling", google_scenario="struggling", out=lambda _: None)
    (session,) = [e for e in fake.events if e.is_planner_event]
    assert session.start == datetime(2026, 11, 9, 10)
    assert (session.end - session.start) == timedelta(hours=5)


# ------------------------------------------------------------------ cli
def cli_demo(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["study_planner", "demo", *args])
    cli.main()


def test_cli_demo_runs_with_a_fixed_date(monkeypatch, tmp_path, capsys):
    cli_demo(monkeypatch, "--handcrafted", "--today", "2026-11-09", "--out", str(tmp_path))
    out = capsys.readouterr().out
    assert "Distinct actions chosen: 4" in out and "MISMATCH" not in out
    assert (tmp_path / "burnt_out.ics").exists()


def test_cli_demo_single_scenario(monkeypatch, tmp_path, capsys):
    cli_demo(monkeypatch, "--scenario", "one_weak_spot", "--today", "2026-11-09", "--out", str(tmp_path))
    assert "Decision: 2.5-hour focused session" in capsys.readouterr().out
    assert [p.name for p in tmp_path.glob("*.ics")] == ["one_weak_spot.ics"]


def test_cli_demo_rejects_unknown_scenario_and_google_without_scenario(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="Unknown scenario"):
        cli_demo(monkeypatch, "--scenario", "nope", "--out", str(tmp_path))
    with pytest.raises(SystemExit, match="pick one student"):
        cli_demo(monkeypatch, "--google", "--out", str(tmp_path))
    assert list(tmp_path.iterdir()) == []  # nothing was written to the calendar or disk
