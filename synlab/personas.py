"""Seeded fictional persona generation."""

from __future__ import annotations

import json
import random
from typing import Any


NAMES = (
    "Alex Morgan", "Sam Rivera", "Taylor Brooks", "Jordan Patel",
    "Casey Nguyen", "Riley Thompson", "Jamie Chen", "Avery Wilson",
    "Morgan Diaz", "Drew Okafor", "Quinn Murphy", "Cameron Shah",
    "Skyler Bennett", "Rowan Kim", "Emery Clarke", "Robin Ali",
    "Charlie Evans", "Reese Campbell", "Finley Park", "Dakota Flores",
)
ROLES = (
    "small business owner", "operations coordinator", "new team member",
    "independent consultant", "support specialist", "community volunteer",
    "project manager", "part-time administrator", "student founder",
    "office manager", "freelance designer", "club treasurer",
)
SKILL_LEVELS = ("novice", "beginner", "intermediate", "advanced", "expert")
GOALS = (
    "organize my account notifications",
    "export a copy of my account data",
    "recover access to my account",
    "update the settings for my team",
    "understand how to manage a subscription",
    "invite a colleague to a workspace",
    "find an earlier activity record",
    "change how weekly summaries are delivered",
    "resolve a sign-in problem",
    "set up a new project space",
    "remove an outdated team member",
    "learn what happens when I close my account",
)
COMMUNICATION_STYLES = (
    "concise", "careful", "casual", "detail-seeking", "direct", "hesitant",
    "polite", "informal",
)


def generate_personas(seed: int, count: int = 100) -> list[dict[str, Any]]:
    """Return fictional personas generated only from the given seed and count."""
    if count < 1:
        raise ValueError("count must be at least 1")

    rng = random.Random(seed)
    personas: list[dict[str, Any]] = []
    for index in range(count):
        personas.append({
            "persona_id": f"persona-{index + 1:04d}",
            "name": rng.choice(NAMES),
            "role": rng.choice(ROLES),
            "skill_level": rng.choice(SKILL_LEVELS),
            "goal": rng.choice(GOALS),
            "patience": rng.randint(1, 5),
            "communication_style": rng.choice(COMMUNICATION_STYLES),
            "tendencies": {
                "typos": rng.randint(0, 100),
                "vague_requests": rng.randint(0, 100),
                "repeated_retries": rng.randint(0, 100),
                "frustration_escalation": rng.randint(0, 100),
            },
        })
    return personas


def personas_json(personas: list[dict[str, Any]]) -> str:
    """Serialize persona data in a stable, UTF-8-friendly representation."""
    return json.dumps(personas, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
