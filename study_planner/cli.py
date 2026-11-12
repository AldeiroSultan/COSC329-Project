"""Command line entry point: python -m study_planner.cli <command>."""

from __future__ import annotations

import argparse


def cmd_simulate(args: argparse.Namespace) -> None:
    from study_planner import config as cfg
    from study_planner.network import state_names
    from study_planner.simulate_data import (
        learned_cpt_parents,
        parent_config_counts,
        simulate_students,
        write_csv,
    )

    df = simulate_students()
    path = write_csv(df)
    print(f"Wrote {len(df)} students (seed {cfg.RANDOM_SEED}) to {path}\n")

    names = state_names()
    counts = parent_config_counts(df)
    print(f"{'CPT':<62}{'params':>7}{'rows/param':>11}{'min rows in a parent config':>29}")
    total_params = 0
    for label, (child, _) in learned_cpt_parents().items():
        series = counts[label]
        params = len(series) * (len(names[child]) - 1)
        total_params += params
        print(f"{label:<62}{params:>7}{len(df) / params:>11.0f}{int(series.min()):>29}")
    print(f"\nTotal free parameters learned: {total_params} ({len(df) / total_params:.0f} rows per parameter)")


def cmd_learn(args: argparse.Namespace) -> None:
    import pandas as pd

    from study_planner import config as cfg
    from study_planner.learning import (
        build_learned_model,
        compare_cpds,
        crosscheck_with_pgmpy,
        learn_cpds,
        learned_variables,
        save_cpds,
    )
    from study_planner.network import state_names

    if not cfg.STUDENTS_CSV.exists():
        raise SystemExit(f"{cfg.STUDENTS_CSV} not found. Run: python -m study_planner.cli simulate")

    cpds = learn_cpds()
    path = save_cpds(cpds)
    build_learned_model().check_model()
    print(f"Learned {len(cpds)} CPTs with Laplace smoothing (alpha={cfg.LAPLACE_ALPHA}) -> {path}\n")

    table = compare_cpds(cpds)
    names = state_names()
    reported = table[table.apply(lambda r: r["state"] == names[r["cpt"]][1], axis=1)]
    print("P(second state of the CPT variable | parents): hand-crafted vs learned")
    print(f"{'CPT':<13}{'parents':<68}{'state':<7}{'hand':>6}{'learned':>9}{'diff':>7}")
    for _, r in reported.iterrows():
        print(f"{r['cpt']:<13}{r['parents']:<68}{r['state']:<7}{r['handcrafted']:>6.3f}{r['learned']:>9.3f}{r['abs_diff']:>7.3f}")
    print(f"\nMean |learned - hand-crafted| over all cells: {table['abs_diff'].mean():.3f} "
          f"(max {table['abs_diff'].max():.3f})")

    df = pd.read_csv(cfg.STUDENTS_CSV)
    worst = max(crosscheck_with_pgmpy(df, node) for node in learned_variables())
    print(f"Max difference vs pgmpy BayesianEstimator(prior_type='K2') over all learned CPTs: {worst:.2e}")


def cmd_demo(args: argparse.Namespace) -> None:
    from datetime import date
    from pathlib import Path

    from study_planner import config as cfg
    from study_planner.demo import run_demo
    from study_planner.scenarios import SCENARIOS, get_model

    names = [s.name for s in SCENARIOS]
    if args.scenario and args.scenario not in names:
        raise SystemExit(f"Unknown scenario {args.scenario!r}. Choose one of: {', '.join(names)}")
    if args.google and not args.scenario:
        raise SystemExit(
            "--google writes to your real calendar and each run replaces today's planner sessions, "
            f"so pick one student with --scenario NAME ({', '.join(names)})."
        )
    today = date.fromisoformat(args.today) if args.today else date.today()
    run_demo(
        get_model(args.handcrafted),
        today,
        Path(args.out) if args.out else cfg.OUTPUT_DIR,
        only=args.scenario,
        google_scenario=args.scenario if args.google else None,
    )


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("study_planner.api:app", host="127.0.0.1", port=args.port, reload=True)


def cmd_figures(args: argparse.Namespace) -> None:
    """Write reproducible report charts from the committed student dataset."""
    from pathlib import Path
    from study_planner import config as cfg
    from study_planner.viz import FIG_DIR, generate_figures

    if not cfg.STUDENTS_CSV.exists():
        raise SystemExit("Student CSV not found. Run: python -m study_planner.cli simulate")
    for path in generate_figures(Path(args.out) if args.out else FIG_DIR):
        print(f"Saved: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="study_planner")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("simulate", help="generate data/processed/students.csv").set_defaults(func=cmd_simulate)
    sub.add_parser("learn", help="learn CPTs with Laplace smoothing").set_defaults(func=cmd_learn)

    demo = sub.add_parser("demo", help="run student scenarios and write calendars")
    demo.add_argument("--scenario", help="run only this student (struggling, advanced, ...)")
    demo.add_argument("--google", action="store_true", help="also write --scenario's plan to Google Calendar")
    demo.add_argument("--handcrafted", action="store_true", help="use hand-crafted instead of learned CPTs")
    demo.add_argument("--today", help="pretend today is YYYY-MM-DD (default: the real date)")
    demo.add_argument("--out", help="folder for the .ics files (default: output/)")
    demo.set_defaults(func=cmd_demo)

    serve = sub.add_parser("serve", help="run the web dashboard")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    figures = sub.add_parser("figures", help="generate report network, CPT and utility charts")
    figures.add_argument("--out", help="output directory (default: docs/figures/)")
    figures.set_defaults(func=cmd_figures)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
