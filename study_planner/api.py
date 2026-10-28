"""FastAPI backend for the dashboard in web/ (branch MF-00007)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from study_planner import config as cfg

app = FastAPI(title="Bayesian Study Planner")


class PlanRequest(BaseModel):
    difficulty: dict[str, str]
    quiz: dict[str, str | None] = {}
    sleep: str | None = None
    exam_date: str           # YYYY-MM-DD
    use_learned: bool = True


@app.get("/api/scenarios")
def get_scenarios() -> list[dict]:
    # TODO(MF-00007): serialize study_planner.scenarios.SCENARIOS
    raise NotImplementedError("MF-00007")


@app.post("/api/plan")
def post_plan(req: PlanRequest) -> dict:
    """Return {posteriors, expected_utility, best_action, events} for the form input.

    TODO(MF-00007): build StudentEvidence, query, decide, plan into an InMemoryCalendarClient.
    """
    raise NotImplementedError("MF-00007")


@app.get("/api/network")
def get_network() -> dict:
    # TODO(MF-00007): nodes + edges (+ CPTs) for drawing the network
    raise NotImplementedError("MF-00007")


app.mount("/", StaticFiles(directory=cfg.ROOT / "web", html=True), name="web")
