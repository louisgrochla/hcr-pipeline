"""Tests for hcr.clean against small synthetic DataFrames.

Synthetic *values* throughout; source column labels are the verbatim
HSE labels from the inspected files (they are load-bearing — the
mapping must match them exactly, trailing spaces and all).
"""

import pandas as pd
import pytest

from hcr import clean, schema


@pytest.fixture
def messy_strings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label": ["  alpha", "beta  ", "ga   mma", None, 7],
            "n": [1, 2, 3, 4, 5],
        }
    )


@pytest.fixture
def era1_raw() -> pd.DataFrame:
    """Minimal era-1-shaped raw frame with verbatim source labels."""
    return pd.DataFrame(
        {
            "HCRDID": [1, 2, 3],
            "Incident Date": ["1999-05-01", "2000-06-02", "2001-07-03"],
            "Severity": ["MINOR", "BLANK", "Significant"],
            "Equivalent hole diameter [mm]": [1, 999, "BLANK"],
            "Estimated quantity released (kg) ": ["10.5", "BLANK", "3"],
            "Non-process/ Process?": ["PROCESS", "NON-PROCESS", "PROCESS"],
            "Non Process Type": [None, "DIESEL", None],
            "Operational Mode - Primary": [
                "NORMAL PRODUCTION  ",
                "NORMAL PRODUCTION",
                "WELLOPS",
            ],
            "not a mapped column": ["x", "y", "z"],
        }
    )


@pytest.fixture
def era2_raw() -> pd.DataFrame:
    """Minimal era-2-shaped raw frame, including an all-empty padding row
    and free-text hole sizes, as observed in the real 2016 sheet."""
    return pd.DataFrame(
        {
            "URN": ["A1", "A2", None],
            "Event Date": ["2016-03-01", "2016-04-01", None],
            "Severity classification of this release\n(classified by HSL)": [
                "Minor",
                "SIGNIFICANT",
                None,
            ],
            "Equivalent hole diameter [mm]": [2.5, "1mm", None],
            " Non Process Type": [None, "DIESEL", None],
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

    def test_input_not_mutated(self, messy_strings):
        before = messy_strings.copy()
        clean.strip_string_whitespace(messy_strings)
        pd.testing.assert_frame_equal(messy_strings, before)


class TestDropExactDuplicates:
    def test_drops_full_row_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        out = clean.drop_exact_duplicates(df)
        assert len(out) == 2 and list(out.index) == [0, 1]


class TestMapToCanonical:
    def test_era1_renames_to_canonical(self, era1_raw):
        out = clean.map_to_canonical(era1_raw, year=2000)
        assert list(out.columns) == list(schema.CANONICAL_COLUMNS)
        assert list(out["record_id"]) == [1, 2, 3]

    def test_unmapped_source_columns_dropped(self, era1_raw):
        out = clean.map_to_canonical(era1_raw, year=2000)
        assert "not a mapped column" not in out.columns

    def test_absent_canonical_columns_are_na(self, era2_raw):
        out = clean.map_to_canonical(era2_raw, year=2016)
        # era 2 has no explicit PROCESS/NON-PROCESS column
        assert out["process_or_non_process"].isna().all()

    def test_unknown_year_raises_keyerror(self, era1_raw):
        with pytest.raises(KeyError):
            clean.map_to_canonical(era1_raw, year=2030)


class TestReplaceBlankSentinel:
    def test_blank_becomes_na(self, era1_raw):
        out = clean.replace_blank_sentinel(era1_raw)
        assert pd.isna(out["Severity"][1])
        assert pd.isna(out["Equivalent hole diameter [mm]"][2])

    def test_non_blank_untouched(self, era1_raw):
        out = clean.replace_blank_sentinel(era1_raw)
        assert out["Severity"][0] == "MINOR"


class TestDropEmptyRows:
    def test_all_na_rows_dropped(self, era2_raw):
        out = clean.drop_empty_rows(clean.map_to_canonical(era2_raw, 2016))
        assert len(out) == 2


class TestNormaliseCategories:
    def test_case_folded_upper(self, era1_raw):
        out = clean.normalise_categories(clean.map_to_canonical(era1_raw, 2000))
        assert out["severity"][2] == "SIGNIFICANT"

    def test_whitespace_variants_merge(self, era1_raw):
        out = clean.normalise_categories(clean.map_to_canonical(era1_raw, 2000))
        assert out["operational_mode_primary"][0] == out["operational_mode_primary"][1]

    def test_record_id_not_case_folded(self):
        df = pd.DataFrame({"record_id": ["abc"], "severity": ["minor"]})
        out = clean.normalise_categories(df)
        assert out["record_id"][0] == "abc"


class TestCoerceTypes:
    def test_dates_numbers_and_strings(self, era1_raw):
        out = clean.coerce_types(
            clean.replace_blank_sentinel(clean.map_to_canonical(era1_raw, 2000))
        )
        assert pd.api.types.is_datetime64_any_dtype(out["event_date"])
        assert out["quantity_released_kg"].dtype == "float64"
        assert out["quantity_released_kg"][0] == 10.5

    def test_free_text_numerics_coerce_to_na(self, era2_raw):
        out = clean.coerce_types(clean.map_to_canonical(era2_raw, 2016))
        assert out["hole_diameter_mm"][0] == 2.5
        assert pd.isna(out["hole_diameter_mm"][1])  # '1mm'


class TestReplaceMissingValueCodes:
    def test_999_hole_code_becomes_na(self):
        df = pd.DataFrame({"hole_diameter_mm": [1.0, 999.0, 50.0]})
        out = clean.replace_missing_value_codes(df)
        assert pd.isna(out["hole_diameter_mm"][1])
        assert out["hole_diameter_mm"][2] == 50.0


class TestDeriveNonProcess:
    def test_era1_uses_explicit_column(self, era1_raw):
        out = clean.derive_non_process(clean.map_to_canonical(era1_raw, 2000))
        assert list(out["non_process"]) == [False, True, False]

    def test_era2_derived_from_type(self, era2_raw):
        canon = clean.drop_empty_rows(clean.map_to_canonical(era2_raw, 2016))
        out = clean.derive_non_process(canon)
        assert list(out["non_process"]) == [False, True]


class TestDropDuplicateRecords:
    def test_dedup_by_record_id(self):
        df = pd.DataFrame(
            {"record_id": [1, 1, 2], "severity": ["MINOR", "MAJOR", "MINOR"]}
        )
        out = clean.drop_duplicate_records(df)
        assert list(out["record_id"]) == [1, 2]
        assert out["severity"][0] == "MINOR"  # first occurrence kept


class TestDropDeliberateReleases:
    def test_filters_non_process_keeps_na(self):
        df = pd.DataFrame(
            {
                "record_id": [1, 2, 3],
                "non_process": pd.array([True, False, None], dtype="boolean"),
            }
        )
        out = clean.drop_deliberate_releases(df)
        assert list(out["record_id"]) == [2, 3]


class TestCleanRecords:
    def test_full_pipeline_era1(self, era1_raw):
        out = clean.clean_records(era1_raw, year=2000)
        assert list(out.columns) == list(schema.CANONICAL_COLUMNS) + ["non_process"]
        assert len(out) == 3
        assert pd.isna(out["hole_diameter_mm"][1])  # 999 sentinel
        assert pd.isna(out["severity"][1])  # BLANK sentinel
        assert out["severity"][2] == "SIGNIFICANT"

    def test_full_pipeline_era2(self, era2_raw):
        out = clean.clean_records(era2_raw, year=2016)
        assert len(out) == 2  # padding row dropped
        assert out["severity"][0] == "MINOR"
        assert list(out["non_process"]) == [False, True]
