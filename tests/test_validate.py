"""Tests for hcr.validate against small synthetic DataFrames.

Rules must return the DataFrame of failing rows, never a bare boolean.
Synthetic column names only — no HSE column names are assumed anywhere.
The named HCR rules blocked on the Day 2 schema are explicitly xfailed.
"""

import pandas as pd
import pytest

from hcr import validate


@pytest.fixture
def numbers() -> pd.DataFrame:
    return pd.DataFrame({"size": [0.5, 1.0, 50.0, -3.0, None, "not a number"]})


@pytest.fixture
def categories() -> pd.DataFrame:
    return pd.DataFrame({"level": ["low", "mid", "high", "LOW", None]})


@pytest.fixture
def dated() -> pd.DataFrame:
    return pd.DataFrame(
        {"when": ["1993-06-01", "1990-01-01", "2020-12-31", "not a date", None]}
    )


class TestNumericWithinBounds:
    def test_returns_failing_rows_not_bool(self, numbers):
        out = validate.numeric_within_bounds(numbers, "size", lower=0.0, upper=100.0)
        assert isinstance(out, pd.DataFrame)

    def test_flags_out_of_bounds_missing_and_non_numeric(self, numbers):
        out = validate.numeric_within_bounds(numbers, "size", lower=0.0, upper=100.0)
        assert list(out.index) == [3, 4, 5]

    def test_bounds_inclusive_and_optional(self, numbers):
        out = validate.numeric_within_bounds(numbers, "size", lower=0.5)
        assert 0 not in out.index  # 0.5 passes an inclusive lower bound
        assert 2 not in out.index  # no upper bound

    def test_all_pass_is_empty(self):
        df = pd.DataFrame({"size": [1, 2, 3]})
        out = validate.numeric_within_bounds(df, "size", lower=0, upper=10)
        assert out.empty


class TestValuesInSet:
    def test_flags_unknown_and_missing(self, categories):
        out = validate.values_in_set(categories, "level", {"low", "mid", "high"})
        # "LOW" fails: category normalisation is clean.py's job, not validation's
        assert list(out.index) == [3, 4]


class TestDatesWithinPeriod:
    def test_flags_outside_unparseable_and_missing(self, dated):
        out = validate.dates_within_period(
            dated, "when", start="1992-10-01", end="2024-12-31"
        )
        assert list(out.index) == [1, 3, 4]


class TestNoDuplicateKeys:
    def test_returns_all_occurrences(self):
        df = pd.DataFrame({"id": [1, 1, 2], "v": ["a", "b", "c"]})
        out = validate.no_duplicate_keys(df, subset=["id"])
        assert list(out.index) == [0, 1]


class TestRunAll:
    def test_summary_shape_and_pass_rate(self, numbers):
        rules = {
            "size_in_bounds": lambda df: validate.numeric_within_bounds(
                df, "size", lower=0.0, upper=100.0
            ),
        }
        summary = validate.run_all(numbers, rules)
        assert list(summary.columns) == [
            "rule",
            "status",
            "n_failing",
            "n_rows",
            "pass_rate",
        ]
        row = summary.iloc[0]
        assert row["rule"] == "size_in_bounds"
        assert row["status"] == "ok"
        assert row["n_failing"] == 3
        assert row["n_rows"] == 6
        assert row["pass_rate"] == pytest.approx(0.5)

    def test_blocked_rules_recorded_not_fatal(self, numbers):
        """The default registry is entirely blocked on the Day 2 schema;
        run_all must document that, not crash."""
        summary = validate.run_all(numbers)
        assert set(summary["status"]) == {"blocked"}
        assert set(summary["rule"]) == set(validate.DEFAULT_RULES)
        assert summary["pass_rate"].isna().all()


# ---------------------------------------------------------------------------
# Named HCR rules blocked on the Day 2 schema — explicit xfails, strict so
# they must be rewritten when the bodies land.
# ---------------------------------------------------------------------------

BLOCKED = pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="blocked on Day 2 schema (real HSE files not yet inspected)",
)


@BLOCKED
def test_hole_size_rule_blocked(numbers):
    validate.hole_size_within_plausible_bounds(numbers)


@BLOCKED
def test_severity_rule_blocked(categories):
    validate.severity_in_permitted_set(categories)


@BLOCKED
def test_date_rule_blocked(dated):
    validate.date_within_reporting_period(dated)


@BLOCKED
def test_cause_rule_blocked(categories):
    validate.cause_category_resolvable(categories)
