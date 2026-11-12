"""Reproducible report figures; run ``python -m study_planner.cli figures``."""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from study_planner import config as cfg
from study_planner.decision import decide
from study_planner.inference import query
from study_planner.learning import build_learned_model, compare_cpds, learn_cpds
from study_planner.network import network_edges, state_names
from study_planner.scenarios import SCENARIOS

FIG_DIR = cfg.ROOT / "docs" / "figures"
BLUE, ORANGE, TEAL, PURPLE = "#31688e", "#d98532", "#228675", "#8566a9"


def _save(fig: Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    return path


def _style(ax: Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)


def draw_network(path: Path = FIG_DIR / "network.png") -> Path:
    """Draw all model edges, with distinct evidence, latent and observable nodes."""
    graph = nx.DiGraph(network_edges())
    pos = {}
    for i, concept in enumerate(cfg.CONCEPTS):
        x = i * 2.8
        pos[cfg.NODE_DIFFICULTY[concept]] = (x, 3)
        pos[cfg.NODE_MASTERY[concept]] = (x, 1.5)
        pos[cfg.NODE_QUIZ[concept]] = (x + 1.3, 1.5)
    pos.update({cfg.NODE_DAYS: (8.4, 3), cfg.NODE_STRESS: (8.4, 1.5),
                cfg.NODE_SLEEP: (9.7, 1.5), cfg.NODE_EXAM: (4.2, -1.6)})
    evidence = {*cfg.NODE_DIFFICULTY.values(), cfg.NODE_DAYS}
    observable = {*cfg.NODE_QUIZ.values(), cfg.NODE_SLEEP}
    colors = [BLUE if node in evidence else TEAL if node in observable else ORANGE
              for node in graph.nodes]
    fig = Figure(figsize=(13, 8))
    ax = fig.subplots()
    nx.draw_networkx_edges(graph, pos, ax=ax, node_size=3100, arrowsize=20,
                           edge_color="#667085", width=1.6)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=3100, node_color=colors,
                           edgecolors="white", linewidths=2)
    labels = {node: node.replace("_", "\n") for node in graph.nodes}
    labels.update({cfg.NODE_DAYS: "Days left", cfg.NODE_EXAM: "Exam\nsuccess"})
    nx.draw_networkx_labels(graph, pos, labels, ax=ax, font_size=10, font_color="white")
    ax.set_title("Bayesian study planner | 13-node network", fontsize=19, pad=24)
    ax.legend(handles=[Patch(color=BLUE, label="Given evidence"),
                       Patch(color=ORANGE, label="Latent / queried"),
                       Patch(color=TEAL, label="Optional observations")],
              loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.set_xlim(-1, 10.7)
    ax.set_ylim(-2.3, 3.9)
    ax.axis("off")
    return _save(fig, path)


def plot_cpt_comparison(path: Path = FIG_DIR / "cpt_comparison.png") -> Path:
    """Compare all nine learned binary CPTs, showing each second state's probability."""
    table = compare_cpds(learn_cpds())
    names = state_names()
    fig = Figure(figsize=(16, 14), layout="constrained")
    axes = fig.subplots(3, 3).flat
    for ax, (node, rows) in zip(axes, table.groupby("cpt", sort=False)):
        rows = rows[rows.state == names[node][1]]
        x = np.arange(len(rows))
        ax.bar(x - 0.19, rows.handcrafted, 0.38, color=BLUE, label="Hand-crafted")
        ax.bar(x + 0.19, rows.learned, 0.38, color=ORANGE, label="Learned")
        labels = [", ".join(part.split("=")[1] for part in value.split(", "))
                  for value in rows.parents]
        if node == cfg.NODE_EXAM:
            labels = [label.replace("low", "L").replace("high", "H").replace(", ", "")
                      for label in labels]
        ax.set_xticks(x, labels, rotation=90 if len(rows) > 5 else 0)
        ax.set_ylim(0, 1)
        ax.set_ylabel(f"P({names[node][1]})")
        ax.set_title(node.replace("_", " "), fontweight="bold")
        parents = rows.parents.iloc[0]
        parent_names = ", ".join(part.split("=")[0] for part in parents.split(", "))
        ax.set_xlabel(parent_names.replace("Mastery_", "Mastery ") +
                      ("\nL = low, H = high" if node == cfg.NODE_EXAM else ""), fontsize=9)
        _style(ax)
    fig.suptitle("Hand-crafted vs learned CPTs\n"
                 "All parent configurations; complementary state has probability 1 - P",
                 fontsize=19)
    fig.legend(handles=[Patch(color=BLUE, label="Hand-crafted"),
                        Patch(color=ORANGE, label="Learned from 5,000 simulated students")],
               loc="outside lower center", ncol=2, frameon=False)
    return _save(fig, path)


def plot_expected_utilities(path: Path = FIG_DIR / "expected_utility.png") -> Path:
    """Plot all actions per scenario using the learned model, marking each winner."""
    model = build_learned_model()
    decisions = [decide(model, query(model, scenario.evidence),
                        cfg.days_bucket(scenario.evidence.days_until_exam)) for scenario in SCENARIOS]
    fig = Figure(figsize=(14, 7), layout="constrained")
    ax = fig.subplots()
    x = np.arange(len(SCENARIOS))
    width = 0.8 / len(cfg.ACTIONS)
    for i, (action, color) in enumerate(zip(cfg.ACTIONS, [BLUE, ORANGE, TEAL, PURPLE])):
        positions = x + (i - (len(cfg.ACTIONS) - 1) / 2) * width
        values = [decision.expected_utility[action.key] for decision in decisions]
        bars = ax.bar(positions, values, width, color=color, label=f"{action.key.title()} ({action.hours:g} h)")
        for bar, decision in zip(bars, decisions):
            if decision.best.key == action.key:
                bar.set_edgecolor("#17212b")
                bar.set_linewidth(2)
        ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=8)
    labels = [s.name.replace("_", " ").title() + f"\n{s.evidence.days_until_exam} days to exam\nBest: {d.best.key}"
              for s, d in zip(SCENARIOS, decisions)]
    ax.set_xticks(x, labels)
    ax.set_ylim(0, max(max(d.expected_utility.values()) for d in decisions) * 1.22)
    ax.set_ylabel("Expected utility (points; higher is better)")
    ax.set_title("Different students, different best actions\nLearned model | outlined bars mark the chosen action",
                 fontsize=18, pad=18)
    ax.legend(loc="upper left", ncol=len(cfg.ACTIONS), frameon=False)
    _style(ax)
    return _save(fig, path)


def generate_figures(out_dir: Path = FIG_DIR) -> list[Path]:
    """Generate all report figures without accessing Google Calendar."""
    return [draw_network(out_dir / "network.png"),
            plot_cpt_comparison(out_dir / "cpt_comparison.png"),
            plot_expected_utilities(out_dir / "expected_utility.png")]
