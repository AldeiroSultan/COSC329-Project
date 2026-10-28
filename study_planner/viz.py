"""Figures for the report, saved to docs/figures/ (branch TI-00004)."""

from __future__ import annotations

from pathlib import Path

from study_planner import config as cfg

FIG_DIR = cfg.ROOT / "docs" / "figures"


def draw_network(path: Path = FIG_DIR / "network.png") -> Path:
    # TODO(TI-00004): networkx DiGraph from network.network_edges(); colour evidence/query/observable nodes
    raise NotImplementedError("TI-00004")


def plot_cpt_comparison(path: Path = FIG_DIR / "cpt_comparison.png") -> Path:
    # TODO(TI-00004): hand-crafted vs learned bars for each learned CPT
    raise NotImplementedError("TI-00004")


def plot_expected_utilities(path: Path = FIG_DIR / "expected_utility.png") -> Path:
    # TODO(TI-00004): grouped bars, one group per scenario, one bar per action
    raise NotImplementedError("TI-00004")
