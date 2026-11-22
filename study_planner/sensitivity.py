"""One-at-a-time sensitivity of the five demo decisions (branch TI-00006).

The action effects, urgency factors and utilities in config.py are our own
assumptions. This module changes one assumption at a time and reports which
students' chosen action changes, to show how much the recommendations depend on them.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from typing import Iterator

from study_planner import config as cfg
from study_planner.decision import decide
from study_planner.inference import query
from study_planner.network import BayesNet
from study_planner.scenarios import SCENARIOS


@contextmanager
def patched_config(overrides: dict) -> Iterator[None]:
    """Temporarily set attributes of study_planner.config, restoring them on exit."""
    saved = {name: getattr(cfg, name) for name in overrides}
    try:
        for name, value in overrides.items():
            setattr(cfg, name, value)
        yield
    finally:
        for name, value in saved.items():
            setattr(cfg, name, value)


def decisions_with(model: BayesNet, overrides: dict | None = None) -> dict[str, str]:
    """Chosen action key per scenario, with `overrides` applied to config.py."""
    with patched_config(overrides or {}):
        return {
            s.name: decide(model, query(model, s.evidence), s.evidence.days_state).best.key
            for s in SCENARIOS
        }


def settings() -> list[tuple[str, str, dict]]:
    """(assumption, new setting, config overrides) for every one-at-a-time change."""
    utility = lambda pass_high: {**cfg.UTILITY, "pass": {**cfg.UTILITY["pass"], "high": pass_high}}
    intense_stress = lambda delta: [replace(a, stress_delta=delta) if a.key == "intense" else a for a in cfg.ACTIONS]
    boosts = lambda scale: [replace(a, mastery_boost=a.mastery_boost * scale) for a in cfg.ACTIONS]
    urgency = lambda scale: {k: min(1.0, v * scale) for k, v in cfg.URGENCY.items()}
    return [
        ("Cost per study hour (1.0)", "0.5", {"TIME_COST_PER_HOUR": 0.5}),
        ("Cost per study hour (1.0)", "2.0", {"TIME_COST_PER_HOUR": 2.0}),
        ("Utility of passing under high stress (85)", "70", {"UTILITY": utility(70.0)}),
        ("Utility of passing under high stress (85)", "95", {"UTILITY": utility(95.0)}),
        ("Stress added by an intense block (+0.20)", "+0.10", {"ACTIONS": intense_stress(0.10)}),
        ("Stress added by an intense block (+0.20)", "+0.30", {"ACTIONS": intense_stress(0.30)}),
        ("All mastery boosts", "x0.75", {"ACTIONS": boosts(0.75)}),
        ("All mastery boosts", "x1.25", {"ACTIONS": boosts(1.25)}),
        ("Urgency factors (1.0 / 0.7 / 0.3)", "x0.75", {"URGENCY": urgency(0.75)}),
        ("Urgency factors (1.0 / 0.7 / 0.3)", "x1.25", {"URGENCY": urgency(1.25)}),
    ]


def run_sensitivity(model: BayesNet) -> tuple[dict[str, str], list[dict]]:
    """Return (baseline decisions, one row per setting).

    Each row: {assumption, setting, decisions, changed} where changed maps a student to
    (baseline action, new action) for every student whose decision differs.
    """
    baseline = decisions_with(model)
    rows = []
    for assumption, setting, overrides in settings():
        new = decisions_with(model, overrides)
        rows.append({
            "assumption": assumption,
            "setting": setting,
            "decisions": new,
            "changed": {name: (baseline[name], action) for name, action in new.items() if action != baseline[name]},
        })
    return baseline, rows


def format_report(baseline: dict[str, str], rows: list[dict]) -> str:
    lines = ["Baseline decisions: " + ", ".join(f"{n}={a}" for n, a in baseline.items()), ""]
    lines.append(f"{'Assumption (baseline)':<44}{'Setting':<8}{'Changed':>8}  Which decisions change")
    for row in rows:
        detail = "; ".join(f"{n}: {old} -> {new}" for n, (old, new) in row["changed"].items()) or "none"
        lines.append(f"{row['assumption']:<44}{row['setting']:<8}{len(row['changed']):>5}/{len(baseline)}  {detail}")
    total = sum(len(row["changed"]) for row in rows)
    lines.append(f"\nDecisions changed in {sum(1 for r in rows if r['changed'])} of {len(rows)} settings "
                 f"({total} of {len(rows) * len(baseline)} student decisions).")
    return "\n".join(lines)
