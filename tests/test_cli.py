import json
import os
import subprocess
import sys
from pathlib import Path


def _run(root, home, *args):
    env = os.environ.copy()
    env["SYNLAB_HOME"] = str(home)
    env["PYTHONPATH"] = str(root)
    return subprocess.run(
        [sys.executable, "-m", "synlab", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_personas_simulate_cluster_report_and_audit(tmp_path):
    root = Path(__file__).resolve().parents[1]
    home = tmp_path / "state"

    personas = _run(root, home, "personas", "--seed", "42", "--count", "3")
    assert personas.returncode == 0
    persona_data = json.loads(personas.stdout)
    assert persona_data["persona_count"] == 3
    assert "All users are simulated" in persona_data["honesty_boundary"]

    simulated = _run(root, home, "simulate", "--seed", "42", "--target", "defects", "--count", "5")
    assert simulated.returncode == 0, simulated.stderr
    assert "All complaints are synthetic" in simulated.stdout
    first_transcripts = (home / "latest-sessions.json").read_bytes()
    first_clusters = (home / "latest-clusters.json").read_bytes()
    first_personas = (home / "latest-personas.json").read_bytes()
    repeated = _run(root, home, "simulate", "--seed", "42", "--target", "defects", "--count", "5")
    assert repeated.returncode == 0, repeated.stderr
    assert (home / "latest-sessions.json").read_bytes() == first_transcripts
    assert (home / "latest-clusters.json").read_bytes() == first_clusters
    assert (home / "latest-personas.json").read_bytes() == first_personas

    clustered = _run(root, home, "cluster")
    assert clustered.returncode == 0, clustered.stderr
    assert "cluster-" in clustered.stdout

    report = _run(root, home, "report", "--format", "md")
    assert report.returncode == 0, report.stderr
    report_path = home / "latest-report.md"
    first_report = report_path.read_bytes()
    assert b"HONESTY BOUNDARY" in first_report
    report_again = _run(root, home, "report", "--format", "md")
    assert report_again.returncode == 0, report_again.stderr
    assert report_path.read_bytes() == first_report
    html_report = _run(root, home, "report", "--format", "html")
    assert html_report.returncode == 0, html_report.stderr
    assert "HONESTY BOUNDARY" in (home / "latest-report.html").read_text(encoding="utf-8")

    audit_records = [json.loads(line) for line in (home / "synlab-audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [record["command"] for record in audit_records] == [
        "personas", "simulate", "simulate", "cluster", "report", "report", "report"
    ]
    assert audit_records[1]["seed"] == 42
    assert audit_records[1]["target"] == "defects"
    assert audit_records[1]["persona_count"] == 5
    assert audit_records[1]["sessions"]
    assert audit_records[1]["failures"]
    assert audit_records[1]["clusters"]
    assert audit_records[1]["timestamp"].endswith("Z")


def test_cli_rejects_non_positive_count(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = _run(root, tmp_path / "state", "personas", "--seed", "1", "--count", "0")
    assert result.returncode != 0
