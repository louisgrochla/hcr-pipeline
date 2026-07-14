"""Tests for hcr.profile against small synthetic DataFrames."""

import pandas as pd
import pytest

from hcr import profile


@pytest.fixture
def yearly() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2000, 2000, 2001, 2001],
            "cat": ["A", "B", "A", None],
            "num": [1.0, None, 3.0, 4.0],
        }
    )


class TestMissingness:
    def test_fraction_missing_per_column_per_year(self, yearly):
        out = profile.missingness_by_column_by_year(yearly, "year")
        assert out.loc[2000, "num"] == 0.5
        assert out.loc[2001, "num"] == 0.0
        assert out.loc[2001, "cat"] == 0.5
        assert "year" not in out.columns


class TestCategoryDrift:
    def test_shares_sum_to_one_and_track_missing(self, yearly):
        out = profile.category_drift(yearly, "cat", "year")
        assert out.loc[2000].sum() == pytest.approx(1.0)
        assert out.loc[2000, "A"] == pytest.approx(0.5)
        # 2001: one A, one missing — missingness visible as its own share
        assert out.loc[2001].drop("A").sum() == pytest.approx(0.5)


class TestNumericDistribution:
    def test_exact_value_frequencies_sorted(self):
        df = pd.DataFrame({"v": [2, 1, 1, "junk", None]})
        out = profile.numeric_distribution(df, "v")
        assert list(out["value"]) == [1.0, 2.0]
        assert list(out["count"]) == [2, 1]
        assert out["share"].sum() == pytest.approx(1.0)


class TestBoundaryConcentration:
    def test_pile_up_at_lower_boundary(self):
        df = pd.DataFrame({"mm": [1.0] * 6 + [1.5, 1.7] + [2.0] * 2 + [50.0, None]})
        out = profile.boundary_concentration(df, "mm", lower=1.0, upper=2.0)
        assert list(out["count"]) == [6, 2, 2]
        assert out["share"].sum() == pytest.approx(1.0)

    def test_out_of_interval_values_excluded(self):
        df = pd.DataFrame({"mm": [0.5, 3.0]})
        out = profile.boundary_concentration(df, "mm")
        assert out["count"].sum() == 0
        assert out["share"].isna().all()


class TestWithEventYear:
    def test_year_derived_from_dates(self):
        df = pd.DataFrame({"event_date": ["1999-05-01", None]})
        out = profile.with_event_year(df)
        assert out["year"][0] == 1999
        assert pd.isna(out["year"][1])
