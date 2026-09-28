"""Persona journeys, fixture execution, and failure detection."""

from __future__ import annotations

import re
from typing import Any

from .targets import FixtureTarget, make_target


FIXED_JOURNEY = (
    "How long does account recovery take?",
    "How long does account recovery take?",
    "Please list the notification settings.",
    "Run a diagnostic for timeout marker 504.",
)


def _failure(
    code: str,
    interaction: dict[str, Any],
    detail: str,
    related_interaction_ids: list[str] | None = None,
) -> dict[str, Any]:
    behavior = interaction.get("target_behavior_code") or "SIMULATED_USER_ESCALATION"
    result = {
        "code": code,
        "signature": f"{code}|{behavior}",
        "interaction_id": interaction["interaction_id"],
        "detail": detail,
    }
    if related_interaction_ids:
        result["related_interaction_ids"] = related_interaction_ids
    return result


def _normalized_question(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _maybe_typo(text: str, tendency: int) -> str:
    if tendency < 55:
        return text
    replacements = (("notifications", "notifcations"), ("account", "acount"), ("export", "expotr"))
    lower = text.lower()
    for original, replacement in replacements:
        if original in lower:
            position = lower.index(original)
            return text[:position] + replacement + text[position + len(original):]
    return text


def _persona_prompt(persona: dict[str, Any]) -> str:
    tendencies = persona["tendencies"]
    if tendencies["vague_requests"] >= 65:
        return "Can you help me with this? I am not sure where to start."
    prompt = f"I need to {persona['goal']}. What should I do?"
    if persona["skill_level"] == "expert":
        prompt = f"I need to {persona['goal']}. Which settings path should I use?"
    return _maybe_typo(prompt, tendencies["typos"])


def _journey(persona: dict[str, Any]) -> list[str]:
    prompts = [_persona_prompt(persona), *FIXED_JOURNEY]
    if persona["tendencies"]["repeated_retries"] >= 55:
        prompts.extend((FIXED_JOURNEY[2],))
    return prompts


def simulate_sessions(
    seed: int,
    target_name: str,
    personas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Execute each scripted persona journey against a fresh local target."""
    sessions: list[dict[str, Any]] = []
    for persona_index, persona in enumerate(personas):
        target: FixtureTarget = make_target(target_name)
        max_wait_ms = 900 + persona["patience"] * 450
        interactions: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        for step, user_input in enumerate(_journey(persona), start=1):
            result = target.handle(user_input)
            timed_out = result.latency_ms > max_wait_ms
            interaction = {
                "interaction_id": f"{persona['persona_id']}-i{step:02d}",
                "target_called": True,
                "user_input": user_input,
                "target_response": None if timed_out else result.response,
                "latency_ms": result.latency_ms,
                "wait_budget_ms": max_wait_ms,
                "timed_out": timed_out,
                "target_behavior_code": result.behavior_code,
            }
            interactions.append(interaction)

            if timed_out:
                failures.append(_failure("TIMEOUT", interaction, "Response exceeded the persona wait budget."))
            elif result.response is None:
                failures.append(_failure("UNANSWERED", interaction, "The target returned no answer."))
            if result.behavior_code == "CONFUSING_RESPONSE":
                failures.append(_failure("CONFUSING_RESPONSE", interaction, "The fixture response uses opaque wording."))
            if not timed_out and result.latency_ms > max(1400, max_wait_ms * 0.7):
                failures.append(_failure("SLOW_RESPONSE", interaction, "Response latency exceeded the slow-response threshold."))

        answers_by_question: dict[str, list[dict[str, Any]]] = {}
        for interaction in interactions:
            if not interaction["target_called"] or interaction["target_response"] is None:
                continue
            question = _normalized_question(interaction["user_input"])
            answers_by_question.setdefault(question, []).append(interaction)
        for answers in answers_by_question.values():
            if len(answers) < 2:
                continue
            response_values = {answer["target_response"] for answer in answers}
            if len(response_values) > 1:
                later = answers[-1]
                failures.append(_failure(
                    "CONTRADICTION",
                    later,
                    "Repeated identical questions received different answers.",
                    [answer["interaction_id"] for answer in answers],
                ))

        substantive_failure_count = sum(
            failure["code"] != "FRUSTRATION_TRIGGER" for failure in failures
        )
        if (
            substantive_failure_count >= 2
            and persona["tendencies"]["frustration_escalation"] >= 55
        ):
            interaction = {
                "interaction_id": f"{persona['persona_id']}-i{len(interactions) + 1:02d}",
                "target_called": False,
                "user_input": "This is frustrating, I have already retried.",
                "target_response": None,
                "latency_ms": 0,
                "wait_budget_ms": max_wait_ms,
                "timed_out": False,
                "target_behavior_code": None,
            }
            interactions.append(interaction)
            failures.append(_failure(
                "FRUSTRATION_TRIGGER",
                interaction,
                "The simulated persona escalated after multiple journey failures.",
            ))

        sessions.append({
            "session_id": f"session-{persona_index + 1:04d}",
            "persona_id": persona["persona_id"],
            "seed": seed,
            "target": target_name,
            "max_wait_ms": max_wait_ms,
            "interactions": interactions,
            "failures": failures,
        })
    return sessions
