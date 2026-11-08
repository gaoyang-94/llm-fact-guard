# factguard

[![tests](https://github.com/gaoyang-94/llm-fact-guard/actions/workflows/tests.yml/badge.svg)](https://github.com/gaoyang-94/llm-fact-guard/actions/workflows/tests.yml)

Verify LLM output against its source before it ships.

An LLM will happily write "revenue grew 42.8%" when the source says 41.2%.
`factguard` makes that failure loud and recoverable: every number, required
field and enum in the output is checked against the source payload, and a
failed check triggers exactly one regeneration before the item is dropped.

Zero dependencies. Standard library only.

## Why

Most LLM pipelines do this:

```python
text = call_model(prompt)
publish(text)          # hope
```

The failure is silent. The number looks plausible, the paragraph reads well,
and the mistake is discovered by a reader two weeks later.

`factguard` inverts the default: nothing ships until it has been checked, and
the check runs in code, not in a prompt.

## Install

```bash
git clone https://github.com/gaoyang-94/llm-fact-guard
cd llm-fact-guard
python3 -m unittest discover -s tests -v
```

## Quickstart

```python
from factguard import Guard, FieldCheck, NumberCheck

guard = Guard([
    FieldCheck("title"),
    NumberCheck("body", source_field="text"),
])

output, report = guard.run(generate, source, max_attempts=2)
if output is None:
    drop(report)   # never ship an unverified item
```

`run()` calls `generate(source, attempt)` first, then on failure calls
`generate(source, attempt, feedback)` with the human-readable failure list, so
the second attempt is a repair rather than a reroll.

## CLI

```bash
python3 -m factguard.cli examples/output_bad.json examples/source.json --rules examples/rules.json
```

```
[PASS] title (required): present
[FAIL] body (traceable_number): number(s) not found in source: 47.8, 1400
2/3 checks passed
```

## Rules

| Rule | What it enforces |
|---|---|
| `FieldCheck` | field exists and is non-empty |
| `NumberCheck` | every number in the output appears in the source text |
| `RegexCheck` | field matches a pattern (dates, IDs) |
| `SetCheck` | field value comes from a fixed vocabulary |

`NumberCheck` compares rendered digits, so `41.2` and `41.20` both match.
Rounding (`41` for `41.2`) is rejected by default; pass `allow_rounding=True`
when your pipeline legitimately rounds.

## Design notes

- **Checks are boring on purpose.** A rule that needs a second model to judge
  is not a check, it is another way to be wrong.
- **One repair attempt, then drop.** Retrying forever hides a broken prompt.
- **The report is data.** `GuardReport` is a list of `CheckResult`s, so it can
  be logged per run and counted over time.

## License

MIT
