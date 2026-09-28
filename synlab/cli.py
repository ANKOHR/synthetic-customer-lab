"""Command line interface for Synthetic Customer Lab."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import HONESTY_BANNER
from .clustering import cluster_sessions
from .personas import generate_personas, personas_json
from .reporting import build_report_data, render_html, render_markdown
from .simulation import simulate_sessions
from .storage import append_audit, load_run, save_run, write_json
from .targets import TARGET_ALIASES


def _positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("count must be an integer") from error
    if count < 1:
        raise argparse.ArgumentTypeError("count must be at least 1")
    return count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synlab",
        description=HONESTY_BANNER,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    personas = commands.add_parser(
        "personas",
        help="generate seeded fictional personas",
        description=HONESTY_BANNER,
    )
    personas.add_argument("--seed", type=int, required=True)
    personas.add_argument("--count", type=_positive_count, default=100)

    simulate = commands.add_parser(
        "simulate",
        help="run persona journeys against a fixture",
        description=HONESTY_BANNER,
    )
    simulate.add_argument("--seed", type=int, required=True)
    simulate.add_argument("--target", required=True, choices=sorted(TARGET_ALIASES))
    simulate.add_argument("--count", type=_positive_count, default=100)

    commands.add_parser(
        "cluster",
        help="cluster failures from the latest simulation",
        description=HONESTY_BANNER,
    )

    report = commands.add_parser(
        "report",
        help="write a weakness report from recorded sessions",
        description=HONESTY_BANNER,
    )
    report.add_argument("--format", required=True, choices=("md", "html"))
    return parser


def _banner() -> None:
    print(f"HONESTY BOUNDARY: {HONESTY_BANNER}")


def _write_personas(seed: int, count: int) -> list[dict[str, Any]]:
    personas = generate_personas(seed, count)
    write_json("latest-personas.json", personas)
    return personas


def _failure_count(sessions: list[dict[str, Any]]) -> int:
    return sum(len(session["failures"]) for session in sessions)


def _audit_for_run(command: str, run: dict[str, Any], clusters: list[dict[str, Any]]) -> None:
    append_audit(
        command=command,
        seed=run.get("seed"),
        target=run.get("target"),
        persona_count=run.get("persona_count", 0),
        sessions=run.get("sessions", []),
        clusters=clusters,
    )


def _run_personas(args: argparse.Namespace) -> int:
    personas = _write_personas(args.seed, args.count)
    append_audit(
        command="personas",
        seed=args.seed,
        target=None,
        persona_count=len(personas),
        sessions=[],
        clusters=[],
    )
    result = {
        "honesty_boundary": HONESTY_BANNER,
        "seed": args.seed,
        "persona_count": len(personas),
        "personas": personas,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _run_simulate(args: argparse.Namespace) -> int:
    personas = _write_personas(args.seed, args.count)
    sessions = simulate_sessions(args.seed, args.target, personas)
    clusters = cluster_sessions(sessions)
    run = {
        "seed": args.seed,
        "target": args.target,
        "persona_count": len(personas),
        "personas": personas,
        "sessions": sessions,
        "clusters": clusters,
    }
    save_run(run)
    write_json("latest-sessions.json", sessions)
    write_json("latest-clusters.json", clusters)
    _audit_for_run("simulate", run, clusters)
    _banner()
    print(
        f"Simulated {len(sessions)} fictional personas against '{args.target}'. "
        f"Recorded {_failure_count(sessions)} failures in {len(clusters)} clusters."
    )
    print("Deterministic artifacts: .synlab/latest-sessions.json and .synlab/latest-clusters.json")
    return 0


def _run_cluster() -> int:
    run = load_run()
    clusters = cluster_sessions(run["sessions"])
    run["clusters"] = clusters
    save_run(run)
    write_json("latest-clusters.json", clusters)
    _audit_for_run("cluster", run, clusters)
    _banner()
    print(f"Built {len(clusters)} deterministic weakness clusters from {len(run['sessions'])} sessions.")
    for cluster in clusters:
        print(f"{cluster['cluster_id']}: {cluster['theme']} ({len(cluster['session_ids'])} sessions)")
    return 0


def _run_report(format_name: str) -> int:
    run = load_run()
    clusters = cluster_sessions(run["sessions"])
    run["clusters"] = clusters
    save_run(run)
    write_json("latest-clusters.json", clusters)
    report_data = build_report_data(clusters, run["sessions"], run["persona_count"])
    if format_name == "md":
        rendered = render_markdown(report_data, run["seed"], run["target"], run["persona_count"])
        filename = "latest-report.md"
    else:
        rendered = render_html(report_data, run["seed"], run["target"], run["persona_count"])
        filename = "latest-report.html"
    from .storage import state_dir

    report_path = state_dir() / filename
    report_path.write_text(rendered, encoding="utf-8", newline="\n")
    _audit_for_run("report", run, clusters)
    _banner()
    print(f"Wrote {format_name} weakness report with {len(report_data)} ranked themes: {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "personas":
            return _run_personas(args)
        if args.command == "simulate":
            return _run_simulate(args)
        if args.command == "cluster":
            return _run_cluster()
        if args.command == "report":
            return _run_report(args.format)
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"HONESTY BOUNDARY: {HONESTY_BANNER}", file=sys.stderr)
        print(f"synlab: {error}", file=sys.stderr)
        return 2
    return 0
