"""Command line entry point: python -m study_planner.cli <command>."""

from __future__ import annotations

import argparse


def cmd_simulate(args: argparse.Namespace) -> None:
    # TODO(MF-00002): simulate_students -> write_csv -> print parent_config_counts summary
    raise NotImplementedError("MF-00002")


def cmd_learn(args: argparse.Namespace) -> None:
    # TODO(MF-00003): learn_cpds -> save_cpds -> print learned vs hand-crafted for each CPT
    raise NotImplementedError("MF-00003")


def cmd_demo(args: argparse.Namespace) -> None:
    # TODO(MF-00006): for each scenario print evidence, posteriors, EU table, chosen action;
    # write output/<scenario>.ics; with --google also push to Google Calendar.
    raise NotImplementedError("MF-00006")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("study_planner.api:app", host="127.0.0.1", port=args.port, reload=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="study_planner")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("simulate", help="generate data/processed/students.csv").set_defaults(func=cmd_simulate)
    sub.add_parser("learn", help="learn CPTs with Laplace smoothing").set_defaults(func=cmd_learn)

    demo = sub.add_parser("demo", help="run student scenarios and write calendars")
    demo.add_argument("--google", action="store_true", help="also write to Google Calendar")
    demo.add_argument("--handcrafted", action="store_true", help="use hand-crafted instead of learned CPTs")
    demo.set_defaults(func=cmd_demo)

    serve = sub.add_parser("serve", help="run the web dashboard")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
