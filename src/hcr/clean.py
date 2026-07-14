"""Cleaning transformations: normalisation, deduplication, type coercion.

Every transformation is a named function with a docstring — no inline
magic. Functions are pure: they take a DataFrame and return a new one.
Raw data is never modified; sentinel handling happens here, not in
:mod:`hcr.ingest`.

The intended order is :func:`clean_records`; each step is also usable
alone.
"""

from __future__ import annotations

import pandas as pd

from hcr import schema


def strip_string_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace and collapse internal runs of
    whitespace (including non-breaking spaces) to a single space, in
    every string-typed column.

    Motivated by observed drift such as ``'NORMAL PRODUCTION  '``
    (2,494 rows) vs ``'NORMAL PRODUCTION'`` (44 rows) being counted as
    distinct categories, and ``\\xa0`` inside era-2 values.
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
    """Drop rows that are exact duplicates across all columns, keeping
    the first occurrence."""
    return df.drop_duplicates(keep="first").reset_index(drop=True)


def map_to_canonical(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Rename a raw table's source columns to the canonical schema and
    reduce to the canonical column set.

    Source labels are matched verbatim (trailing spaces, embedded
    newlines and all) against ``schema.source_mapping_for_year(year)``.
    Canonical columns absent from the source era (e.g.
    ``process_or_non_process`` in era 2, ``system_quaternary`` naming
    differences) come out as all-NA. Unmapped source columns are dropped
    from the canonical view — the raw data remains available via
    :mod:`hcr.ingest`.
    """
    mapping = schema.source_mapping_for_year(year)
    out = df.rename(columns=mapping)
    return out.reindex(columns=list(schema.CANONICAL_COLUMNS))


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that contain no data at all (every column NA).

    Motivated by 16 fully-empty padding rows observed in the
    ``HCRs 2016 Final`` sheet.
    """
    return df.dropna(how="all").reset_index(drop=True)


def replace_blank_sentinel(df: pd.DataFrame) -> pd.DataFrame:
    """Replace era 1's literal ``'BLANK'`` missing-value sentinel
    (43,149 cells across 85 columns in the raw file) with real NA.

    Matched case-sensitively after stripping surrounding whitespace.
    """
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(
            out[col]
        ):
            out[col] = out[col].map(
                lambda v: (
                    pd.NA
                    if isinstance(v, str) and v.strip() == schema.BLANK_SENTINEL
                    else v
                )
            )
    return out


def normalise_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise categorical text to uppercase with collapsed
    whitespace, resolving observed case drift (era 2 ``'Minor'`` vs
    ``'MINOR'``, ``'Awaiting Classification'`` vs era 1's
    ``'AWAITING CLASSIFICATION'``).

    This is deliberately *lossless* normalisation only (case +
    whitespace). Synonym mapping across eras (e.g. era 1 ``WELLOPS`` vs
    ``WELL OPERATION``, era 2 free-text cause entries) changes meaning
    and belongs in an explicit, reviewable mapping table —
    TODO: extend that table from the failing rows reported by
    :func:`hcr.validate.cause_category_resolvable`.

    Applied to canonical categorical/string columns except free-ish
    identifier and numeric-bearing fields.
    """
    exclude = {"record_id", "event_date", "hole_diameter_mm", "quantity_released_kg"}
    out = strip_string_whitespace(df)
    for col in out.columns:
        if col in exclude:
            continue
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(
            out[col]
        ):
            out[col] = out[col].map(lambda v: v.upper() if isinstance(v, str) else v)
    return out


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce canonical columns to their canonical dtypes.

    Numeric and date coercion uses ``errors='coerce'``: unparseable
    values become NA rather than raising, because era 2 mixes free text
    into numeric fields (observed hole-size entries include ``'1mm'``,
    ``'<5'``, ``'1.00 - 2.00'``, ``'Two holes: 10mm and 5mm'``,
    ``'QUERIED'``). The information lost here is exactly what
    :func:`hcr.profile.missingness_by_column_by_year` and the validation
    rules quantify downstream.
    """
    out = df.copy()
    for col, dtype in schema.CANONICAL_COLUMNS.items():
        if col not in out.columns:
            continue
        if dtype.startswith("datetime"):
            out[col] = pd.to_datetime(out[col], errors="coerce")
        elif dtype.startswith("float") or dtype.startswith("int"):
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = out[col].astype(dtype)
    return out


def replace_missing_value_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Replace numeric missing-value codes with NA. Currently: hole
    diameter ``999`` (era 1's unknown-size code, 163 records).

    Run after :func:`coerce_types` (operates on numeric values).
    """
    out = df.copy()
    if "hole_diameter_mm" in out.columns:
        out["hole_diameter_mm"] = out["hole_diameter_mm"].where(
            ~out["hole_diameter_mm"].isin(schema.HOLE_DIAMETER_SENTINELS_MM)
        )
    return out


def derive_non_process(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean ``non_process`` column — the agreed proxy for
    releases outside the process inventory (diesel, lube oil, etc.).

    Era 1 has an explicit ``process_or_non_process`` column
    (PROCESS/NON-PROCESS); era 2 does not, so there a row is non-process
    iff ``non_process_type`` is populated. Neither era carries an
    explicit deliberate-release flag; see :func:`drop_deliberate_releases`
    for the documented limitation.
    """
    out = df.copy()
    explicit = out.get("process_or_non_process")
    from_type = out.get("non_process_type")
    non_process = pd.Series(pd.NA, index=out.index, dtype="boolean")
    if from_type is not None:
        non_process = from_type.notna().astype("boolean")
    if explicit is not None:
        explicit = explicit.astype("string")  # an all-NA column arrives as float
        has_explicit = explicit.notna()
        non_process[has_explicit] = (
            explicit[has_explicit].str.strip().str.upper() == "NON-PROCESS"
        )
    out["non_process"] = non_process
    return out


def drop_duplicate_records(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by record identity (``record_id``), keeping the first
    occurrence of each key.

    In the received files both keys are already unique (``HCRDID``
    4,656/4,656; ``URN`` 622/622 after padding rows are dropped), so
    this is a safeguard for future data drops rather than an active fix.
    """
    return df.drop_duplicates(subset=["record_id"], keep="first").reset_index(drop=True)


def apply_category_synonyms(df: pd.DataFrame) -> pd.DataFrame:
    """Consolidate category values via the explicit synonym table
    ``schema.CATEGORY_SYNONYMS`` (spelling variants, typos,
    abbreviations, and sub-values with an unambiguous parent — e.g.
    ``'IMPROPER MAINTENACE'`` → ``'IMPROPER'``, era 1's own ``'WELLOPS'``
    vs ``'WELL OPERATION'``).

    Runs after :func:`normalise_categories` (the table is keyed on
    case/whitespace-normalised values). Values not in the table pass
    through unchanged: sentence-length free text and era-2 categories
    with no era-1 home (EXCURSION, OVERFLOW families) deliberately stay
    as-is and keep failing
    :func:`hcr.validate.cause_category_resolvable` — the honest
    measurement of the taxonomy loss. Every table entry is documented in
    ``reports/schema_mapping.md``.
    """
    out = df.copy()
    for col, synonyms in schema.CATEGORY_SYNONYMS.items():
        if col in out.columns:
            out[col] = out[col].map(lambda v: synonyms.get(v, v))
    return out


def drop_deliberate_releases(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to rows not flagged ``non_process``.

    **Documented limitation (agreed decision: flag, don't drop):** the
    public data has no explicit deliberate-release flag, so
    ``non_process`` is a proxy, and deliberate *process* releases (e.g.
    planned blowdowns appearing under operational mode
    ``SHUTTING DOWN/SHUTDOWN/BLOWDOWN``) cannot be reliably isolated.
    This function is therefore an *opt-in* filter for analyses that want
    process releases only — the default pipeline keeps all rows and the
    flag. Rows with an undetermined flag (NA) are kept.
    """
    if "non_process" not in df.columns:
        df = derive_non_process(df)
    return df.loc[~df["non_process"].fillna(False)].reset_index(drop=True)


def clean_records(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Full cleaning pipeline for one raw source table.

    Order matters: sentinel replacement precedes type coercion (so
    ``'BLANK'`` doesn't turn into a coercion casualty silently), and
    category normalisation precedes validation-facing derivations.
    Deliberate/non-process releases are flagged, never dropped.
    """
    out = map_to_canonical(df, year)
    out = drop_empty_rows(out)
    out = replace_blank_sentinel(out)
    out = normalise_categories(out)
    out = apply_category_synonyms(out)
    out = coerce_types(out)
    out = replace_missing_value_codes(out)
    out = derive_non_process(out)
    out = drop_duplicate_records(out)
    return out
