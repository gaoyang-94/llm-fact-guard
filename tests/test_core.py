import json
import unittest

from factguard import FieldCheck, Guard, NumberCheck, RegexCheck, SetCheck


class FieldCheckTests(unittest.TestCase):
    def test_missing_field_fails(self):
        report = Guard([FieldCheck("title")]).check({}, {})
        self.assertFalse(report.ok)

    def test_present_field_passes(self):
        report = Guard([FieldCheck("title")]).check({"title": "hello"}, {})
        self.assertTrue(report.ok)


class NumberCheckTests(unittest.TestCase):
    def test_number_must_exist_in_source(self):
        source = {"text": "revenue grew 41.2% in Q3"}
        rules = [NumberCheck("body", source_field="text")]
        bad = Guard(rules).check({"body": "revenue grew 42.8% in Q3"}, source)
        self.assertFalse(bad.ok)
        good = Guard(rules).check({"body": "revenue grew 41.2% in Q3"}, source)
        self.assertTrue(good.ok)

    def test_rounding_is_rejected_by_default(self):
        source = {"text": "41.2%"}
        report = Guard([NumberCheck("body")]).check({"body": "about 41%"}, source)
        self.assertFalse(report.ok)

    def test_rounding_can_be_allowed(self):
        source = {"text": "41.2%"}
        rule = NumberCheck("body", allow_rounding=True)
        report = Guard([rule]).check({"body": "about 41%"}, source)
        self.assertTrue(report.ok)

    def test_missing_source_field_fails_loudly(self):
        report = Guard([NumberCheck("body")]).check({"body": "1"}, {})
        self.assertFalse(report.ok)
        self.assertIn("missing", report.failures[0].detail)


class OtherRuleTests(unittest.TestCase):
    def test_regex_check(self):
        rule = RegexCheck("date", pattern=r"\d{4}-\d{2}-\d{2}")
        self.assertTrue(Guard([rule]).check({"date": "2026-11-08"}, {}).ok)
        self.assertFalse(Guard([rule]).check({"date": "08/11/2026"}, {}).ok)

    def test_set_check(self):
        rule = SetCheck("tone", allowed=["dry", "warm"])
        self.assertTrue(Guard([rule]).check({"tone": "dry"}, {}).ok)
        self.assertFalse(Guard([rule]).check({"tone": "hype"}, {}).ok)


class RetryLoopTests(unittest.TestCase):
    def test_regenerates_once_then_succeeds(self):
        source = {"text": "41.2%"}
        calls = {"n": 0}

        def generate(src, attempt, feedback=None):
            calls["n"] += 1
            if attempt == 1:
                return {"body": "42.8%"}
            return {"body": "41.2%"}

        out, report = Guard([NumberCheck("body")]).run(generate, source)
        self.assertIsNotNone(out)
        self.assertTrue(report.ok)
        self.assertEqual(calls["n"], 2)

    def test_returns_none_after_final_failure(self):
        source = {"text": "41.2%"}

        def generate(src, attempt, feedback=None):
            return {"body": "42.8%"}

        out, report = Guard([NumberCheck("body")]).run(generate, source, max_attempts=2)
        self.assertIsNone(out)
        self.assertFalse(report.ok)


if __name__ == "__main__":
    unittest.main()
