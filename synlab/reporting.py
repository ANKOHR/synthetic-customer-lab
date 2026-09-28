"""Deterministic Markdown and HTML weakness reports."""

from __future__ import annotations

import html
from typing import Any

from . import HONESTY_BANNER


def _severity(rate: float, failure_codes: list[str]) -> str:
    if rate >= 0.5:
        return "Critical"
    if rate >= 0.2 or ("TIMEOUT" in failure_codes and rate >= 0.1):
        return "High"
    if rate >= 0.05:
        return "Medium"
    return "Low"


def _excerpt_for(
    cluster: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, str]:
    relevant_ids = {
        item["interaction_id"] for item in cluster["evidence"]
        if item["session_id"] == session["session_id"]
    }
    interaction = next(
        item for item in session["interactions"] if item["interaction_id"] in relevant_ids
    )
    response = interaction["target_response"]
    return {
        "pointer": f"{session['session_id']}#{interaction['interaction_id']}",
        "user_input": interaction["user_input"],
        "target_response": response if response is not None else "[no response]",
    }


def build_report_data(
    clusters: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    persona_count: int,
) -> list[dict[str, Any]]:
    session_map = {session["session_id"]: session for session in sessions}
    ranked: list[dict[str, Any]] = []
    for cluster in clusters:
        members = [session_id for session_id in cluster["session_ids"] if session_id in session_map]
        rate = len(members) / persona_count if persona_count else 0.0
        excerpts = [
            _excerpt_for(cluster, session_map[session_id])
            for session_id in members[:2]
        ]
        ranked.append({
            **cluster,
            "affected_personas": len(members),
            "persona_count": persona_count,
            "affected_rate": rate,
            "severity": _severity(rate, cluster["failure_codes"]),
            "representative_excerpts": excerpts,
        })
    ranked.sort(key=lambda item: (
        {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}[item["severity"]],
        item["affected_personas"],
        item["failure_count"],
        item["theme"],
    ), reverse=True)
    return ranked


def render_markdown(data: list[dict[str, Any]], seed: int, target: str, persona_count: int) -> str:
    lines = [
        "# Synthetic Customer Lab Weakness Report",
        "",
        f"> **HONESTY BOUNDARY:** {HONESTY_BANNER}",
        "",
        f"Seed: `{seed}`  ",
        f"Target: `{target}`  ",
        f"Simulated personas: `{persona_count}`",
        "",
        "All measurements below are calculated from the recorded synthetic sessions.",
        "",
    ]
    if not data:
        lines.extend(("No weakness clusters were found in the recorded sessions.", ""))
        return "\n".join(lines)
    lines.extend(("## Ranked weakness themes", ""))
    for rank, item in enumerate(data, start=1):
        shared_ngrams = ", ".join(
            f"`{gram['text']}` ({gram['session_support']})"
            for gram in item["transcript_ngrams"]
        ) or "none"
        lines.extend((
            f"### {rank}. {item['theme']}",
            "",
            f"Severity: **{item['severity']}**  ",
            f"Affected sessions: **{item['affected_personas']} of {persona_count}** "
            f"({item['affected_rate']:.1%})  ",
            f"Failure occurrences: **{item['failure_count']}**  ",
            f"Cluster: `{item['cluster_id']}`",
            "",
            "Evidence signals:",
            "",
            f"- Failure codes: {', '.join(f'`{code}`' for code in item['failure_codes'])}",
            f"- Target behavior codes: {', '.join(f'`{code}`' for code in item['target_behavior_codes'])}",
            f"- Shared transcript n-grams: {shared_ngrams}",
            "",
            "Representative excerpts:",
            "",
        ))
        for excerpt in item["representative_excerpts"]:
            lines.extend((
                f"- Evidence pointer: `{excerpt['pointer']}`",
                f"  - Simulated input: {excerpt['user_input']}",
                f"  - Fixture response: {excerpt['target_response']}",
            ))
        lines.append("")
    return "\n".join(lines)


def render_html(data: list[dict[str, Any]], seed: int, target: str, persona_count: int) -> str:
    banner = html.escape(HONESTY_BANNER)
    pieces = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Synthetic Customer Lab Weakness Report</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        ".honesty{border-left:4px solid #a33;padding:.8rem 1rem;background:#fff4ed}"
        "code{background:#f1f1f1;padding:.1rem .25rem}li{margin:.4rem 0}</style>",
        "</head><body>",
        "<h1>Synthetic Customer Lab Weakness Report</h1>",
        f'<p class="honesty"><strong>HONESTY BOUNDARY:</strong> {banner}</p>',
        f"<p>Seed: <code>{seed}</code><br>Target: <code>{html.escape(target)}</code><br>"
        f"Simulated personas: <code>{persona_count}</code></p>",
        "<p>All measurements below are calculated from the recorded synthetic sessions.</p>",
    ]
    if not data:
        pieces.append("<p>No weakness clusters were found in the recorded sessions.</p>")
    else:
        pieces.append("<h2>Ranked weakness themes</h2>")
    for rank, item in enumerate(data, start=1):
        pieces.extend((
            f"<section><h3>{rank}. {html.escape(item['theme'])}</h3>",
            f"<p>Severity: <strong>{item['severity']}</strong><br>"
            f"Affected sessions: <strong>{item['affected_personas']} of {persona_count}</strong> "
            f"({item['affected_rate']:.1%})<br>Failure occurrences: <strong>{item['failure_count']}</strong><br>"
            f"Cluster: <code>{item['cluster_id']}</code></p>",
            "<h4>Evidence signals</h4><ul>",
            f"<li>Failure codes: {html.escape(', '.join(item['failure_codes']))}</li>",
            f"<li>Target behavior codes: {html.escape(', '.join(item['target_behavior_codes']))}</li>",
            f"<li>Shared transcript n-grams: {html.escape(', '.join(gram['text'] for gram in item['transcript_ngrams']) or 'none')}</li>",
            "</ul><h4>Representative excerpts</h4><ul>",
        ))
        for excerpt in item["representative_excerpts"]:
            pieces.append(
                f"<li>Evidence pointer: <code>{html.escape(excerpt['pointer'])}</code><br>"
                f"Simulated input: {html.escape(excerpt['user_input'])}<br>"
                f"Fixture response: {html.escape(excerpt['target_response'])}</li>"
            )
        pieces.append("</ul></section>")
    pieces.append("</body></html>")
    return "\n".join(pieces) + "\n"
