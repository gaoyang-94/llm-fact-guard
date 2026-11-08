"""Minimal CLI: validate a JSON pair (output + source) with a rules file."""

import argparse
import json
import sys

from .core import FieldCheck, Guard, NumberCheck, RegexCheck


def build_rules(spec: dict) -> list:
    rules = []
    for item in spec.get("required", []):
        rules.append(FieldCheck(field=item))
    for item in spec.get("numbers", []):
        rules.append(NumberCheck(field=item.get("field"), source_field=item.get("source_field", "text")))
    for item in spec.get("patterns", []):
        rules.append(RegexCheck(field=item["field"], pattern=item["pattern"]))
    return rules


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify LLM output against its source")
    parser.add_argument("output", help="JSON file with the model output")
    parser.add_argument("source", help="JSON file with the source facts")
    parser.add_argument("--rules", required=True, help="JSON file describing the checks")
    args = parser.parse_args(argv)

    with open(args.output) as fh:
        output = json.load(fh)
    with open(args.source) as fh:
        source = json.load(fh)
    with open(args.rules) as fh:
        spec = json.load(fh)

    report = Guard(build_rules(spec)).check(output, source)
    for check in report.checks:
        print(check)
    print(f"\n{report.summary()}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
