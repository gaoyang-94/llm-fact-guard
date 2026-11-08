"""Core verification rules.

The idea is deliberately boring: an LLM may write anything, but a number, a date
or a required field must be traceable to the source payload. Everything else is
opinion and is allowed to vary.
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .report import CheckResult, GuardReport

NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


@dataclass
class Rule:
    """Base class: a rule inspects one field of the output."""

    field: str
    name: str = "rule"

    def check(self, output: dict, source: dict) -> CheckResult:  # pragma: no cover
        raise NotImplementedError


@dataclass
class FieldCheck(Rule):
    """Field must exist and be non-empty in the output."""

    name: str = "required"

    def check(self, output: dict, source: dict) -> CheckResult:
        value = output.get(self.field)
        passed = value is not None and value != "" and value != []
        return CheckResult(
            field=self.field,
            rule=self.name,
            passed=passed,
            detail="present" if passed else "missing or empty",
            expected="non-empty",
            actual=value,
        )


@dataclass
class NumberCheck(Rule):
    """Every number in the output field must appear in the source text.

    This is the check that catches a model inventing "42.8%" when the source
    says "41.2%". Comparison is done on the rendered digits, so 41.2 and 41.20
    both match; a rounded 41 is accepted only when allow_rounding is True.
    """

    source_field: str = "text"
    name: str = "traceable_number"
    allow_rounding: bool = False
    tolerance: float = 0.0

    def check(self, output: dict, source: dict) -> CheckResult:
        raw = output.get(self.field)
        haystack = source.get(self.source_field)
        if haystack is None:
            return CheckResult(self.field, self.name, False, f"source field {self.source_field!r} missing")

        text_out = _as_text(raw)
        text_src = _as_text(haystack)
        if not text_out.strip():
            return CheckResult(self.field, self.name, False, "output field is empty")

        src_numbers = {_norm(n) for n in NUMBER_RE.findall(text_src)}
        missing = []
        for token in NUMBER_RE.findall(text_out):
            if _norm(token) in src_numbers:
                continue
            if self.allow_rounding and self._rounding_match(token, text_src):
                continue
            missing.append(token)

        if missing:
            return CheckResult(
                self.field,
                self.name,
                False,
                f"number(s) not found in source: {', '.join(missing[:5])}",
                expected=sorted(src_numbers)[:8],
                actual=missing,
            )
        return CheckResult(self.field, self.name, True, "all numbers traceable to source")

    def _rounding_match(self, token: str, source_text: str) -> bool:
        try:
            value = float(token)
        except ValueError:
            return False
        for candidate in NUMBER_RE.findall(source_text):
            try:
                if abs(float(candidate) - value) <= max(self.tolerance, 0.5):
                    return True
            except ValueError:
                continue
        return False


@dataclass
class RegexCheck(Rule):
    """Field must match a pattern (dates, IDs, currency codes...)."""

    pattern: str = r".+"
    name: str = "pattern"

    def check(self, output: dict, source: dict) -> CheckResult:
        value = _as_text(output.get(self.field))
        passed = bool(re.fullmatch(self.pattern, value))
        return CheckResult(
            self.field,
            self.name,
            passed,
            "matches pattern" if passed else f"does not match {self.pattern}",
            expected=self.pattern,
            actual=value,
        )


@dataclass
class SetCheck(Rule):
    """Field value must be one of a fixed vocabulary."""

    allowed: Iterable[str] = ()
    name: str = "allowed_values"

    def check(self, output: dict, source: dict) -> CheckResult:
        value = output.get(self.field)
        allowed = list(self.allowed)
        passed = value in allowed
        return CheckResult(
            self.field,
            self.name,
            passed,
            "allowed" if passed else f"{value!r} not in allowed set",
            expected=allowed,
            actual=value,
        )


class Guard:
    """Runs rules over an output payload and reports what failed."""

    def __init__(self, rules: list):
        self.rules = list(rules)

    def check(self, output: dict, source: dict) -> GuardReport:
        return GuardReport([rule.check(output, source) for rule in self.rules])

    def run(
        self,
        generate: Callable[[dict, int], dict],
        source: dict,
        max_attempts: int = 2,
    ) -> tuple:
        """Generate, verify, retry once with the failure list, then give up.

        Returns (output_or_None, report). A None output means the item must be
        dropped rather than shipped — the policy most pipelines get wrong.
        """
        feedback = None
        report = GuardReport()
        for attempt in range(1, max_attempts + 1):
            output = generate(source, attempt) if feedback is None else generate(source, attempt, feedback)
            report = self.check(output, source)
            if report.ok:
                return output, report
            feedback = [str(c) for c in report.failures]
        return None, report


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _norm(token: str) -> str:
    try:
        return f"{float(token.replace(',', '')):g}"
    except ValueError:
        return token
