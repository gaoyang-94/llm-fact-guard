"""Result objects produced by a Guard run."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    """Outcome of a single check against a single field."""

    field: str
    rule: str
    passed: bool
    detail: str = ""
    expected: Any = None
    actual: Any = None

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"[{mark}] {self.field} ({self.rule}): {self.detail}"


@dataclass
class GuardReport:
    """Aggregate outcome for one LLM output payload."""

    checks: list = field(default_factory=list)

    @property
    def failures(self) -> list:
        return [c for c in self.checks if not c.passed]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def checked(self) -> int:
        return len(self.checks)

    def summary(self) -> str:
        return f"{self.checked - len(self.failures)}/{self.checked} checks passed"

    def raise_if_failed(self) -> None:
        if self.failures:
            lines = "\n".join(str(c) for c in self.failures)
            raise ValueError(f"{len(self.failures)} check(s) failed:\n{lines}")
