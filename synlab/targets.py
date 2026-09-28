"""Local scripted fixture targets. No network calls are made."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TargetResult:
    response: str | None
    latency_ms: int
    behavior_code: str


class FixtureTarget(Protocol):
    name: str

    def handle(self, user_input: str) -> TargetResult: ...


@dataclass
class HappyPathTarget:
    name: str = "happy"

    def handle(self, user_input: str) -> TargetResult:
        normalized = user_input.lower()
        if "account recovery" in normalized or "recover access" in normalized:
            response = "Use the account recovery page and follow its identity check steps."
        elif "notification" in normalized or "summary" in normalized:
            response = "Open Settings, choose Notifications, then save your preferences."
        elif "export" in normalized or "data" in normalized:
            response = "Open Settings, choose Data, and request an account export."
        elif "timeout marker" in normalized:
            response = "The diagnostic completed. No action is needed for marker 504."
        else:
            response = "Open Settings and choose the section that matches your goal."
        return TargetResult(response, 80 + (len(user_input) * 3 % 41), "ANSWERED")


@dataclass
class SlowConfusingTarget:
    """A deterministic fixture that is delayed and uses opaque wording."""

    delay_ms: int = 2200
    name: str = "slow"

    def handle(self, user_input: str) -> TargetResult:
        response = (
            "Initiate the relevant workflow, then reconcile the account-level "
            "configuration state with the applicable control surface."
        )
        return TargetResult(response, self.delay_ms + len(user_input) % 301, "CONFUSING_RESPONSE")


@dataclass
class PlantedDefectTarget:
    """A fixture with reproducible dropped, inconsistent, and slow inputs."""

    timeout_delay_ms: int = 5000
    name: str = "defects"
    _recovery_answers: int = 0

    def handle(self, user_input: str) -> TargetResult:
        normalized = " ".join(user_input.lower().split())
        if "account recovery" in normalized:
            self._recovery_answers += 1
            days = 2 if self._recovery_answers % 2 else 7
            return TargetResult(
                f"Account recovery typically takes {days} days.",
                450 + self._recovery_answers * 10,
                "INCONSISTENT_ACCOUNT_RECOVERY",
            )
        if "notification settings" in normalized:
            return TargetResult(None, 260, "DROPPED_NOTIFICATION_SETTINGS")
        if "timeout marker 504" in normalized:
            return TargetResult(
                "The diagnostic is still running.",
                self.timeout_delay_ms,
                "TIMEOUT_DIAGNOSTIC_504",
            )
        return TargetResult(
            "Open Settings and choose the section that matches your goal.",
            110,
            "ANSWERED",
        )


TARGET_ALIASES = {
    "happy": "happy",
    "happy-path": "happy",
    "happy_path": "happy",
    "slow": "slow",
    "slow-confusing": "slow",
    "slow_confusing": "slow",
    "defects": "defects",
    "planted-defects": "defects",
    "planted_defects": "defects",
}


def make_target(name: str) -> FixtureTarget:
    canonical = TARGET_ALIASES.get(name.lower())
    if canonical == "happy":
        return HappyPathTarget()
    if canonical == "slow":
        return SlowConfusingTarget()
    if canonical == "defects":
        return PlantedDefectTarget()
    choices = ", ".join(sorted(TARGET_ALIASES))
    raise ValueError(f"unknown target {name!r}; available names: {choices}")
