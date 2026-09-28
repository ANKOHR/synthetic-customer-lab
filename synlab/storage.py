"""Local deterministic artifacts and append-only run audit log."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def state_dir() -> Path:
    configured = os.environ.get("SYNLAB_HOME")
    destination = Path(configured).expanduser() if configured else Path.cwd() / ".synlab"
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_json(filename: str, value: Any) -> Path:
    path = state_dir() / filename
    path.write_text(encode_json(value), encoding="utf-8", newline="\n")
    return path


def read_json(filename: str) -> Any:
    path = state_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"{path.name} does not exist yet, run 'synlab simulate' first")
    return json.loads(path.read_text(encoding="utf-8"))


def append_audit(
    *,
    command: str,
    seed: int | None,
    target: str | None,
    persona_count: int,
    sessions: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> None:
    path = state_dir() / "synlab-audit.jsonl"
    failure_codes: dict[str, int] = {}
    for session in sessions:
        for failure in session.get("failures", []):
            code = failure["code"]
            failure_codes[code] = failure_codes.get(code, 0) + 1
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "command": command,
        "seed": seed,
        "target": target,
        "persona_count": persona_count,
        "sessions": [session["session_id"] for session in sessions],
        "session_count": len(sessions),
        "failures": failure_codes,
        "failure_count": sum(failure_codes.values()),
        "clusters": [cluster["cluster_id"] for cluster in clusters],
        "cluster_count": len(clusters),
    }
    with path.open("a", encoding="utf-8", newline="\n") as audit_file:
        audit_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def load_run() -> dict[str, Any]:
    return read_json("latest-run.json")


def save_run(value: dict[str, Any]) -> Path:
    return write_json("latest-run.json", value)
