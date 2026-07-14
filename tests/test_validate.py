"""Tests for hcr.validate against small synthetic DataFrames.

Rules must return the DataFrame of failing rows, never a bare boolean.
Named HCR rules operate on canonical (cleaned) column names.
"""

import pandas as pd
import pytest

from hcr import validate


@pytest.fixture
def numbers() -> pd.DataFrame:
    return pd.DataFrame({"size": [0.5, 1.0, 50.0, -3.0, None, "not a number"]})


@pytest.fixture
def canonical() -> pd.DataFrame:
    """Minimal cleaned canonical frame exercising every named rule."""
    return pd.DataFrame(
        {
            "record_id": ["a", "b", "c", "d"],
            "event_date": pd.to_datetime(
                ["1992-09-26", "1999-06-01", "2016-05-05", None]
            ),
            "severity": ["MINOR", "NON-PROCESS", "AWAITING CLASSIFICATION", None],
            "hole_diameter_mm": [1.0, 0.0, 1200.0, None],
            "design_failure": [
                "NO DESIGN FAILURE",
                None,
                "Re-design return line",
                None,
            ],
            "equipment_failure_primary": ["CORROSION", "OTHER", None, None],
            "operational_failure_primary": [
                None,
                "LEFT OPEN",
                "Improper maintenace",
                None,
            ],
            "procedural_failure_primary": [None, None, None, None],
        }
    )


class TestGenericPrimitives:
    def test_numeric_within_bounds_returns_failing_rows(self, numbers):
        out = validate.numeric_within_bounds(numbers, "size", lower=0.0, upper=100.0)
        assert isinstance(out, pd.DataFrame)
        assert list(out.index) == [3, 4, 5]

    def test_values_in_set_flags_unknown_and_missing(self):
        df = pd.DataFrame({"level": ["low", "LOW", None]})
        out = validate.values_in_set(df, "level", {"low"})
        assert list(out.index) == [1, 2]

    def test_dates_within_period(self):
        df = pd.DataFrame({"when": ["1993-06-01", "1990-01-01", "bad", None]})
        out = validate.dates_within_period(df, "when", "1992-10-01", "2021-12-31")
        assert list(out.index) == [1, 2, 3]

    def test_no_duplicate_keys_returns_all_occurrences(self):
        df = pd.DataFrame({"id": [1, 1, 2]})
        out = validate.no_duplicate_keys(df, subset=["id"])
        assert list(out.index) == [0, 1]


class TestHoleSizeRule:
    def test_flags_nonpositive_and_oversized_only(self, canonical):
        out = validate.hole_size_within_plausible_bounds(canonical)
        assert list(out["record_id"]) == ["b", "c"]

    def test_missing_does_not_fail(self, canonical):
        out = validate.hole_size_within_plausible_bounds(canonical)
        assert "d" not in list(out["record_id"])


class TestSeverityRule:
    def test_flags_non_severity_value_and_missing(self, canonical):
        out = validate.severity_in_permitted_set(canonical)
        assert list(out["record_id"]) == ["b", "d"]

    def test_awaiting_classification_is_permitted(self, canonical):
        out = validate.severity_in_permitted_set(canonical)
        assert "c" not in list(out["record_id"])


class TestDateRule:
    def test_flags_pre_collection_and_missing(self, canonical):
        out = validate.date_within_reporting_period(canonical)
        # 1992-09-26 predates the 1 Oct 1992 collection start
        assert list(out["record_id"]) == ["a", "d"]


class TestCauseRule:
    def test_flags_present_but_unresolvable_values(self, canonical):
        out = validate.cause_category_resolvable(canonical)
        # 'c' has free-text design + operational entries; 'b' and 'a'
        # resolve; all-missing 'd' does not fail
        assert list(out["record_id"]) == ["c"]

    def test_missing_causes_do_not_fail(self, canonical):
        out = validate.cause_category_resolvable(canonical)
        assert "d" not in list(out["record_id"])


class TestRunAll:
    def test_summary_shape_and_pass_rates(self, canonical):
        summary = validate.run_all(canonical)
        assert list(summary.columns) == [
            "rule",
            "status",
            "n_failing",
            "n_rows",
            "pass_rate",
        ]
        assert set(summary["rule"]) == set(validate.DEFAULT_RULES)
        assert (summary["status"] == "ok").all()
        by_rule = summary.set_index("rule")
        assert by_rule.loc["severity_in_permitted_set", "n_failing"] == 2
        assert by_rule.loc["severity_in_permitted_set", "pass_rate"] == pytest.approx(
            0.5
        )

    def test_blocked_rules_recorded_not_fatal(self, canonical):
        def not_ready(df):
            raise NotImplementedError("needs more data")

        summary = validate.run_all(canonical, {"future_rule": not_ready})
        assert summary.iloc[0]["status"] == "blocked"
        assert pd.isna(summary.iloc[0]["pass_rate"])

    def test_custom_rules_mapping(self, numbers):
        rules = {
            "size_in_bounds": lambda df: validate.numeric_within_bounds(
                df, "size", lower=0.0, upper=100.0
            ),
        }
        summary = validate.run_all(numbers, rules)
        assert summary.iloc[0]["n_failing"] == 3
        assert summary.iloc[0]["pass_rate"] == pytest.approx(0.5)
