"""factguard — verify LLM output against its source before it ships."""

from .core import FieldCheck, Guard, NumberCheck, RegexCheck, Rule, SetCheck
from .report import CheckResult, GuardReport

__all__ = ["Guard", "Rule", "FieldCheck", "NumberCheck", "RegexCheck", "SetCheck",
           "CheckResult", "GuardReport"]
__version__ = "0.1.0"
