"""Dashboard API: validated evidence and an isolated, in-memory daily plan."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from study_planner import config as cfg
from study_planner.calendar_api import Exam, InMemoryCalendarClient
from study_planner.inference import StudentEvidence
from study_planner.learning import build_learned_model, parents_of
from study_planner.network import BayesNet, build_handcrafted_model, network_edges, state_names
from study_planner.planner import StudyPlanner
from study_planner.scenarios import SCENARIOS

app = FastAPI(title="Bayesian Study Planner")


def get_today() -> date:
    """Use the planner's time zone, independent of the browser/server locale."""
    return datetime.now(ZoneInfo(cfg.TIMEZONE)).date()


class PlanRequest(BaseModel):
    """Student evidence; unknown observations are optional, difficulty is required."""
    model_config = ConfigDict(extra="forbid")
    difficulty: dict[str, str]
    quiz: dict[str, str | None] = Field(default_factory=dict)
    sleep: str | None = None
    exam_date: date
    use_learned: bool = True

    @field_validator("difficulty")
    @classmethod
    def valid_difficulty(cls, value: dict[str, str]) -> dict[str, str]:
        if set(value) != set(cfg.CONCEPTS):
            raise ValueError("Provide a difficulty for every concept: " + ", ".join(cfg.CONCEPTS))
        if any(state not in cfg.DIFFICULTY_STATES for state in value.values()):
            raise ValueError("Difficulty must be " + ", ".join(cfg.DIFFICULTY_STATES))
        return value

    @field_validator("quiz")
    @classmethod
    def valid_quiz(cls, value: dict[str, str | None]) -> dict[str, str | None]:
        if not set(value) <= set(cfg.CONCEPTS):
            raise ValueError("Unknown quiz concept")
        if any(state is not None and state not in cfg.QUIZ_STATES for state in value.values()):
            raise ValueError("Quiz must be low, high or unknown (null)")
        return value

    @field_validator("sleep")
    @classmethod
    def valid_sleep(cls, value: str | None) -> str | None:
        if value is not None and value not in cfg.SLEEP_STATES:
            raise ValueError("Sleep must be poor, good or unknown (null)")
        return value


@lru_cache(maxsize=2)
def load_model(use_learned: bool) -> BayesNet:
    """Cache immutable models for the server lifetime; restart after changing data."""
    if use_learned:
        if not cfg.STUDENTS_CSV.exists():
            raise HTTPException(503, "Learned data is missing. Run simulate, or choose the hand-crafted model.")
        return build_learned_model()
    return build_handcrafted_model()


@app.get("/api/scenarios")
def get_scenarios() -> list[dict]:
    """Return demo evidence and exam dates relative to today in the planner zone."""
    today = get_today()
    return [{"name": s.name, "description": s.description,
             "difficulty": s.evidence.difficulty, "quiz": s.evidence.quiz,
             "sleep": s.evidence.sleep, "days_until_exam": s.evidence.days_until_exam,
             "exam_date": (today + timedelta(days=s.evidence.days_until_exam)).isoformat(),
             "expected_action": s.expected_action} for s in SCENARIOS]


@app.post("/api/plan")
def post_plan(req: PlanRequest) -> dict:
    """Calculate today's recommendation without reading/writing a real calendar."""
    today = get_today()
    if req.exam_date < today:
        raise HTTPException(422, "Choose an exam date on or after today")
    model = load_model(req.use_learned)
    evidence = StudentEvidence(req.difficulty, (req.exam_date - today).days, req.quiz, req.sleep)
    result = StudyPlanner(model, InMemoryCalendarClient()).plan_today(
        today, Exam("Course exam", req.exam_date), evidence)
    decision = result.decision
    events = [{"summary": e.summary, "start": e.start.replace(tzinfo=ZoneInfo(cfg.TIMEZONE)).isoformat(),
               "end": e.end.replace(tzinfo=ZoneInfo(cfg.TIMEZONE)).isoformat(),
               "description": e.description} for e in result.events_created]
    return {"posteriors": asdict(decision.posteriors),
            "expected_utility": decision.expected_utility, "best_action": decision.best.key,
            "action_label": decision.best.label, "hours": decision.best.hours,
            "target_concept": decision.target_concept, "events": events,
            "today": today.isoformat(), "exam_date": req.exam_date.isoformat(),
            "days_until_exam": evidence.days_until_exam, "timezone": cfg.TIMEZONE,
            "model": "learned" if req.use_learned else "handcrafted"}


@app.get("/api/network")
def get_network(use_learned: bool = True) -> dict:
    """Return graph, state definitions and CPTs for the selected model."""
    model = load_model(use_learned)
    names = state_names()
    roots = {*cfg.NODE_DIFFICULTY.values(), cfg.NODE_DAYS}
    observed = {*cfg.NODE_QUIZ.values(), cfg.NODE_SLEEP}
    return {"today": get_today().isoformat(), "timezone": cfg.TIMEZONE,
            "model": "learned" if use_learned else "handcrafted", "concepts": cfg.CONCEPTS,
            "difficulty_states": cfg.DIFFICULTY_STATES, "quiz_states": cfg.QUIZ_STATES,
            "sleep_states": cfg.SLEEP_STATES,
            "actions": [asdict(action) for action in cfg.ACTIONS],
            "nodes": [{"id": node, "states": states,
                       "role": "evidence" if node in roots else "observation" if node in observed else "query"}
                      for node, states in names.items()],
            "edges": [{"source": source, "target": target} for source, target in network_edges()],
            "cpds": {cpd.variable: {"states": names[cpd.variable],
                                    "parents": parents_of(cpd.variable),
                                    "parent_states": {p: names[p] for p in parents_of(cpd.variable)},
                                    "values": cpd.get_values().tolist()}
                     for cpd in model.get_cpds()}}


app.mount("/", StaticFiles(directory=cfg.ROOT / "web", html=True), name="web")
