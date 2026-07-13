"""Tests for hcr.clean against small synthetic DataFrames.

Synthetic column names only — no HSE column names are assumed anywhere.
Functions blocked on the Day 2 schema are explicitly xfailed with
``raises=NotImplementedError``: they must fail for that exact reason,
and the xfail flips to a failure the moment they gain a real body
(``strict=True``), forcing the tests to be rewritten alongside.
"""

import pandas as pd
import pytest

from hcr import clean


@pytest.fixture
def messy_strings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label": ["  alpha", "beta  ", "ga   mma", None, 7],
            "n": [1, 2, 3, 4, 5],
        }
    )


@pytest.fixture
def with_duplicates() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": [1, 1, 2, 3],
            "b": ["x", "x", "y", "z"],
        }
    )


class TestStripStringWhitespace:
    def test_strips_and_collapses(self, messy_strings):
        out = clean.strip_string_whitespace(messy_strings)
        assert list(out["label"][:3]) == ["alpha", "beta", "ga mma"]

    def test_non_strings_untouched(self, messy_strings):
        out = clean.strip_string_whitespace(messy_strings)
        assert pd.isna(out["label"][3])
        assert out["label"][4] == 7
        assert list(out["n"]) == [1, 2, 3, 4, 5]

    def test_input_not_mutated(self, messy_strings):
        before = messy_strings.copy()
        clean.strip_string_whitespace(messy_strings)
        pd.testing.assert_frame_equal(messy_strings, before)


class TestDropExactDuplicates:
    def test_drops_full_row_duplicates(self, with_duplicates):
        out = clean.drop_exact_duplicates(with_duplicates)
        assert len(out) == 3
        assert list(out["a"]) == [1, 2, 3]

    def test_keeps_partial_matches(self):
        df = pd.DataFrame({"a": [1, 1], "b": ["x", "y"]})
        out = clean.drop_exact_duplicates(df)
        assert len(out) == 2

    def test_index_reset(self, with_duplicates):
        out = clean.drop_exact_duplicates(with_duplicates)
        assert list(out.index) == [0, 1, 2]


# ---------------------------------------------------------------------------
# Blocked on the Day 2 schema — explicit xfails, strict so they must be
# rewritten when the bodies land.
# ---------------------------------------------------------------------------

BLOCKED = pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="blocked on Day 2 schema (real HSE files not yet inspected)",
)


@BLOCKED
def test_map_to_canonical_blocked(with_duplicates):
    clean.map_to_canonical(with_duplicates, year=1993)


@BLOCKED
def test_coerce_types_blocked(with_duplicates):
    clean.coerce_types(with_duplicates)


@BLOCKED
def test_normalise_categories_blocked(with_duplicates):
    clean.normalise_categories(with_duplicates)


@BLOCKED
def test_drop_duplicate_records_blocked(with_duplicates):
    clean.drop_duplicate_records(with_duplicates)


@BLOCKED
def test_drop_deliberate_releases_blocked(with_duplicates):
    clean.drop_deliberate_releases(with_duplicates)
