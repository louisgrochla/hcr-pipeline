"""Cleaning transformations: normalisation, deduplication, type coercion.

Every transformation is a named function with a docstring — no inline
magic. Functions are pure: they take a DataFrame and return a new one.

Functions that depend on the not-yet-inspected HSE schema raise
:class:`NotImplementedError` with a message stating exactly what they
need. Generic transformations (whitespace, exact-duplicate rows) are
implemented and tested now.
"""

from __future__ import annotations

import pandas as pd

from hcr import schema


# ---------------------------------------------------------------------------
# Implemented now — schema-independent
# ---------------------------------------------------------------------------


def strip_string_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace and collapse internal runs of
    whitespace to a single space, in every string-typed column.

    Non-string columns and non-string values (NaN, numbers) pass through
    untouched. Schema-independent, so implemented now.
    """
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(
            out[col]
        ):
            out[col] = out[col].map(
                lambda v: " ".join(v.split()) if isinstance(v, str) else v
            )
    return out


def drop_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that are exact duplicates across all columns, keeping the
    first occurrence.

    Schema-independent, so implemented now. Key-based deduplication (same
    incident reported twice with differing fields) needs the real record
    identifier — see :func:`drop_duplicate_records`.
    """
    return df.drop_duplicates(keep="first").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Blocked on Day 2 schema — explicit NotImplementedError, per spec
# ---------------------------------------------------------------------------


def map_to_canonical(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Rename a raw year's source columns to the canonical schema.

    Blocked: needs ``schema.YEAR_TO_SOURCE_COLUMNS`` filled from the real
    files (Day 2).
    """
    mapping = schema.source_mapping_for_year(year)  # raises while schema empty
    return df.rename(columns=mapping)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce canonical columns to their canonical dtypes.

    Blocked: needs ``schema.CANONICAL_COLUMNS`` (names + dtypes) and a
    look at how the real files encode dates and numerics (strings? Excel
    serials? banded categories?) before coercion rules can be written.
    """
    if not schema.CANONICAL_COLUMNS:
        raise NotImplementedError(
            "coerce_types needs schema.CANONICAL_COLUMNS (canonical names + "
            "dtypes) and the observed raw encodings of dates/numerics from "
            "the real HSE files. Fill schema.py (Day 2) first."
        )
    return df.astype(schema.CANONICAL_COLUMNS)


def normalise_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Map free-text and inconsistent categorical entries onto canonical
    category sets (severity, cause taxonomy, equipment type).

    Blocked: needs the distinct observed values of each categorical
    column per year from the real files. Do not invent HSE category
    values.
    """
    raise NotImplementedError(
        "normalise_categories needs the distinct observed values of every "
        "categorical column (severity, cause + sub-category, equipment type) "
        "per year from the real files, and canonical target sets agreed in "
        "schema.py. Fill schema.py (Day 2) first."
    )


def drop_duplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by record identity (same incident reported more than
    once, possibly with differing fields), not by exact row equality.

    Blocked: needs to know whether the real files carry a release/incident
    identifier, and if not, which canonical columns jointly identify a
    record.
    """
    raise NotImplementedError(
        "drop_duplicate_records needs the real record identifier column (or "
        "an agreed composite key) from the inspected files. Use "
        "drop_exact_duplicates for whole-row duplicates in the meantime."
    )


def drop_deliberate_releases(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out deliberate releases, keeping unintentional
    loss-of-containment events only.

    Blocked: needs to know how (and in which years) the real files flag
    deliberate releases.
    """
    raise NotImplementedError(
        "drop_deliberate_releases needs the column/values that flag "
        "deliberate releases in the real files, and whether that flag "
        "exists in every reporting year."
    )
