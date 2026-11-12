"""Dashboard contract and validation tests; no real Calendar access."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from study_planner import api, config as cfg
from study_planner.scenarios import SCENARIOS

TODAY = date(2026, 11, 12)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "get_today", lambda: TODAY)
    with TestClient(api.app) as client:
        yield client


def payload(scenario=SCENARIOS[0]):
    return {"difficulty": scenario.evidence.difficulty, "quiz": scenario.evidence.quiz,
            "sleep": scenario.evidence.sleep,
            "exam_date": (TODAY + timedelta(days=scenario.evidence.days_until_exam)).isoformat()}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
@pytest.mark.parametrize("learned", [True, False])
def test_api_scenario_actions_and_event_durations(client, scenario, learned):
    response = client.post("/api/plan", json={**payload(scenario), "use_learned": learned})
    assert response.status_code == 200
    plan = response.json()
    assert plan["best_action"] == scenario.expected_action
    assert plan["today"] == TODAY.isoformat()
    assert plan["model"] == ("learned" if learned else "handcrafted")
    assert set(plan["expected_utility"]) == {action.key for action in cfg.ACTIONS}
    assert plan["best_action"] == max(plan["expected_utility"], key=plan["expected_utility"].get)
    for probability in [*plan["posteriors"]["p_mastery_high"].values(), plan["posteriors"]["p_pass"], plan["posteriors"]["p_stress_high"]]:
        assert 0 <= probability <= 1
    if scenario.expected_action == "rest":
        assert plan["events"] == [] and plan["hours"] == 0
    else:
        from datetime import datetime
        event, = plan["events"]
        start, end = datetime.fromisoformat(event["start"]), datetime.fromisoformat(event["end"])
        assert start.date() == TODAY and start.utcoffset() is not None
        assert (end - start).total_seconds() / 3600 == plan["hours"]


@pytest.mark.parametrize("change", [
    {"difficulty": {"C1": "easy"}},
    {"difficulty": {"C1": "impossible", "C2": "easy", "C3": "easy"}},
    {"difficulty": {"C1": "easy", "C2": "easy", "C3": "easy", "C4": "easy"}},
    {"quiz": {"C4": "high"}}, {"quiz": {"C1": "medium"}},
    {"sleep": "excellent"}, {"exam_date": "not-a-date"},
    {"exam_date": "2026-11-11"}, {"google": True},
])
def test_api_rejects_invalid_evidence(client, change):
    assert client.post("/api/plan", json={**payload(), **change}).status_code == 422


def test_today_exam_unknown_observations_and_requests_are_isolated(client):
    data = {**payload(), "exam_date": TODAY.isoformat(), "quiz": {}, "sleep": None}
    first = client.post("/api/plan", json=data).json()
    second = client.post("/api/plan", json=data).json()
    assert first == second
    assert first["days_until_exam"] == 0
    assert len(first["events"]) <= 1


def test_scenarios_return_relative_dates(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    assert len(response.json()) == len(SCENARIOS)
    for data, scenario in zip(response.json(), SCENARIOS):
        assert data["exam_date"] == (TODAY + timedelta(days=scenario.evidence.days_until_exam)).isoformat()
        assert data["expected_action"] == scenario.expected_action


@pytest.mark.parametrize("learned", [True, False])
def test_network_tables_are_complete_and_normalized(client, learned):
    response = client.get("/api/network", params={"use_learned": learned})
    assert response.status_code == 200
    network = response.json()
    assert len(network["nodes"]) == 13
    assert len(network["edges"]) == 12
    assert set(network["cpds"]) == {node["id"] for node in network["nodes"]}
    for cpd in network["cpds"].values():
        assert set(cpd["parents"]) == set(cpd["parent_states"])
        for column in zip(*cpd["values"]):
            assert sum(column) == pytest.approx(1)


def test_missing_learned_data_returns_actionable_error(client, monkeypatch, tmp_path):
    api.load_model.cache_clear()
    monkeypatch.setattr(cfg, "STUDENTS_CSV", tmp_path / "missing.csv")
    try:
        response = client.post("/api/plan", json=payload())
        assert response.status_code == 503
        assert "simulate" in response.json()["detail"]
        assert client.post("/api/plan", json={**payload(), "use_learned": False}).status_code == 200
    finally:
        api.load_model.cache_clear()


def test_static_app_and_credentials_not_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/app.js").status_code == 200
    for path in ["/credentials.json", "/token.json", "/.git/config", "/api/missing"]:
        assert client.get(path).status_code == 404
