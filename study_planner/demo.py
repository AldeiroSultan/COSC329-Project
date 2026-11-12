"""Console demo: different students -> different plans (branch MF-00006).

Used by `python -m study_planner.cli demo`. Output is plain ASCII so it prints
correctly in any Windows console.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from study_planner import config as cfg
from study_planner.calendar_api import Exam, IcsCalendarClient
from study_planner.inference import StudentEvidence
from study_planner.network import BayesNet
from study_planner.planner import PlanResult, StudyPlanner
from study_planner.scenarios import DEMO_EXAM_NAME, SCENARIOS, Scenario, simulate_two_weeks

TWO_WEEK_SCENARIOS = ("struggling", "advanced")


def describe_evidence(evidence: StudentEvidence) -> str:
    parts = ["difficulty " + ", ".join(f"{c}={d}" for c, d in evidence.difficulty.items())]
    quizzes = {c: q for c, q in evidence.quiz.items() if q is not None}
    parts.append("quizzes " + (", ".join(f"{c}={q}" for c, q in quizzes.items()) if quizzes else "none yet"))
    parts.append(f"sleep {evidence.sleep or 'unknown'}")
    return "; ".join(parts)


def print_plan(result: PlanResult, out: Callable[[str], None]) -> None:
    decision, post = result.decision, result.decision.posteriors
    out(f"Exam: {result.exam.course} on {result.exam.exam_date:%a %b %d} ({result.evidence.days_until_exam} days left)")
    out("Beliefs (from the Bayes net): P(mastery high) " + ", ".join(f"{c} {p:.0%}" for c, p in post.p_mastery_high.items())
        + f"; P(stress high) {post.p_stress_high:.0%}; P(pass) {post.p_pass:.0%}")
    ranked = sorted(decision.expected_utility.items(), key=lambda kv: -kv[1])
    out("Expected utility: " + "   ".join(f"{k} {v:.1f}" + ("  <-- best" if k == decision.best.key else "") for k, v in ranked))
    out(f"Decision: {decision.best.label}")
    for event in result.events_created:
        out(f"Calendar: {event.summary}  {event.start:%a %b %d %H:%M}-{event.end:%H:%M}")
    if not result.events_created:
        out(f"Calendar: no study session today ({result.events_cleared} planner session(s) cleared)")


def print_two_weeks(name: str, rows: list[dict], out: Callable[[str], None]) -> None:
    out(f"14-day run: {name}")
    out(f"{'Day':>3} {'Date':<11}{'Left':>4}  {'Action':<8}{'Hrs':>4}{'EU':>7}{'P(pass)':>9}  {'True mastery C1/C2/C3':<24}Quizzes")
    for r in rows:
        mastery = "/".join(f"{m:.2f}" for m in r["mastery"].values())
        quizzes = "".join(q[0].upper() for q in r["quiz"].values()) or "-"
        out(f"{r['day']:>3} {r['date']:%a %b %d}  {r['days_left']:>4}  {r['action']:<8}{r['hours']:>4.1f}{r['eu']:>7.1f}{r['p_pass']:>9.0%}  {mastery:<24}{quizzes}")
    out(f"Total study hours: {sum(r['hours'] for r in rows):.1f}\n")


def run_demo(
    model: BayesNet,
    today: date,
    out_dir: Path = cfg.OUTPUT_DIR,
    only: str | None = None,
    google_scenario: str | None = None,
    out: Callable[[str], None] = print,
) -> list[dict]:
    """Run the scenarios, print the story and write one .ics per scenario into out_dir.

    only: run just this scenario. google_scenario: also write that one scenario's plan
    to the real Google Calendar (never all of them: each run replaces today's planner
    sessions, so five scenarios would overwrite each other).
    Returns one summary dict per scenario.
    """
    scenarios = [s for s in SCENARIOS if only in (None, s.name)]
    summary = []
    for scenario in scenarios:
        out(f"=== {scenario.name} ===")
        out(scenario.description)
        out("Evidence: " + describe_evidence(scenario.evidence))
        calendar = IcsCalendarClient(out_dir / f"{scenario.name}.ics")
        exam = Exam(DEMO_EXAM_NAME, today + timedelta(days=scenario.evidence.days_until_exam))
        result = StudyPlanner(model, calendar).plan_today(today, exam, scenario.evidence)
        print_plan(result, out)
        out(f"Saved: {calendar.save()}\n")
        summary.append({
            "scenario": scenario.name,
            "action": result.decision.best.key,
            "hours": result.decision.best.hours,
            "expected": scenario.expected_action,
            "match": result.decision.best.key == scenario.expected_action,
        })

    out("=== Summary: same system, different students, different plans ===")
    out(f"{'Student':<16}{'Chosen action':<15}{'Hours':>6}  Expected")
    for row in summary:
        out(f"{row['scenario']:<16}{row['action']:<15}{row['hours']:>6.1f}  {row['expected']}" + ("" if row["match"] else "   <-- MISMATCH"))
    out(f"Distinct actions chosen: {len({row['action'] for row in summary})}\n")

    for scenario in scenarios:
        if scenario.name in TWO_WEEK_SCENARIOS:
            calendar = IcsCalendarClient(out_dir / f"two_week_{scenario.name}.ics")
            rows = simulate_two_weeks(scenario, model, calendar=calendar, today=today)
            print_two_weeks(scenario.name, rows, out)
            out(f"Saved: {calendar.save()}\n")

    if google_scenario:
        write_to_google(model, today, next(s for s in SCENARIOS if s.name == google_scenario), out)
    return summary


def write_to_google(model: BayesNet, today: date, scenario: Scenario, out: Callable[[str], None]) -> PlanResult:
    """Plan `scenario` for today directly on the user's Google Calendar."""
    from study_planner.calendar_api.google_calendar import GoogleCalendarClient

    out(f"=== Google Calendar: {scenario.name} ===")
    exam = Exam(DEMO_EXAM_NAME, today + timedelta(days=scenario.evidence.days_until_exam))
    result = StudyPlanner(model, GoogleCalendarClient()).plan_today(today, exam, scenario.evidence)
    print_plan(result, out)
    out("Written to your Google Calendar (only [BayesPlanner] events are ever touched).")
    return result
