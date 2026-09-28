"""Hand-built deterministic complaint clustering."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any


THEMES = {
    "TIMEOUT": "Requests exceed the wait budget",
    "CONTRADICTION": "Repeated questions receive conflicting answers",
    "UNANSWERED": "Requests receive no answer",
    "FRUSTRATION_TRIGGER": "Repeated failures trigger frustration",
    "CONFUSING_RESPONSE": "Responses are difficult to understand",
    "SLOW_RESPONSE": "Responses exceed the expected pace",
}
THEME_ORDER = {code: index for index, code in enumerate(THEMES)}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _ngrams(text: str) -> set[str]:
    words = _tokens(text)
    return {
        " ".join(words[start:start + size])
        for size in (2, 3)
        for start in range(max(0, len(words) - size + 1))
    }


def _theme_for(failure: dict[str, Any]) -> tuple[str, str]:
    code = failure["code"]
    if code in THEMES:
        return code, THEMES[code]
    behavior = failure["signature"].split("|", 1)[-1]
    words = _ngrams(failure.get("detail", ""))
    phrase = sorted(words)[0] if words else behavior.lower().replace("_", " ")
    fallback = f"OTHER:{behavior}:{phrase}"
    return fallback, f"Related failures around {phrase}"


def cluster_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group failures by shared failure signatures and target behavior codes.

    Shared transcript bigrams and trigrams are then counted across member
    sessions and retained as transparent evidence for each rule-based group.
    Unknown failure codes use their behavior code and detail n-grams as a
    deterministic fallback theme.
    """
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    session_lookup = {session["session_id"]: session for session in sessions}
    for session in sessions:
        for failure in session["failures"]:
            theme_key, title = _theme_for(failure)
            behavior_code = failure["signature"].split("|", 1)[-1]
            group_key = (theme_key, behavior_code)
            group = groups.setdefault(group_key, {
                "theme_key": theme_key,
                "theme": title,
                "failure_codes": set(),
                "failure_signatures": set(),
                "target_behavior_codes": set(),
                "occurrences": [],
                "session_ids": set(),
                "session_ngrams": defaultdict(set),
            })
            group["failure_codes"].add(failure["code"])
            group["failure_signatures"].add(failure["signature"])
            group["target_behavior_codes"].add(behavior_code)
            group["session_ids"].add(session["session_id"])
            group["occurrences"].append({
                "session_id": session["session_id"],
                "interaction_id": failure["interaction_id"],
                "failure_code": failure["code"],
            })
            interaction = next(
                item for item in session["interactions"]
                if item["interaction_id"] == failure["interaction_id"]
            )
            text = interaction["user_input"] + " " + (failure.get("detail") or "")
            group["session_ngrams"][session["session_id"]].update(_ngrams(text))

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (
            THEME_ORDER.get(group["theme_key"], len(THEME_ORDER)),
            group["theme_key"],
            sorted(group["target_behavior_codes"]),
        ),
    )
    clusters: list[dict[str, Any]] = []
    for index, group in enumerate(ordered_groups, start=1):
        session_ids = sorted(group["session_ids"])
        ngram_support: dict[str, int] = defaultdict(int)
        for grams in group["session_ngrams"].values():
            for gram in grams:
                ngram_support[gram] += 1
        minimum_support = max(1, math.ceil(len(session_ids) * 0.2))
        ranked_ngrams = sorted(
            ((gram, support) for gram, support in ngram_support.items() if support >= minimum_support),
            key=lambda item: (-item[1], item[0]),
        )[:8]
        clusters.append({
            "cluster_id": f"cluster-{index:03d}",
            "theme": group["theme"],
            "failure_codes": sorted(group["failure_codes"]),
            "failure_signatures": sorted(group["failure_signatures"]),
            "target_behavior_codes": sorted(group["target_behavior_codes"]),
            "transcript_ngrams": [
                {"text": gram, "session_support": support}
                for gram, support in ranked_ngrams
            ],
            "session_ids": session_ids,
            "failure_count": len(group["occurrences"]),
            "evidence": sorted(
                group["occurrences"],
                key=lambda item: (item["session_id"], item["interaction_id"], item["failure_code"]),
            ),
        })

    valid_ids = set(session_lookup)
    for cluster in clusters:
        cluster["session_ids"] = [session_id for session_id in cluster["session_ids"] if session_id in valid_ids]
    return clusters
