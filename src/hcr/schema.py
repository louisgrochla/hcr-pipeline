"""Canonical schema and year-to-source-column mapping for the HCR data.

**Both tables below are deliberately EMPTY.** They are the Day 2
deliverable and can only be filled after inspecting the real HSE files —
inventing HSE column names here would poison everything downstream.

TODO(Day 2): fill CANONICAL_COLUMNS and YEAR_TO_SOURCE_COLUMNS.
To do that, the following must be seen from the real ``data/raw/`` files
(run ``hcr.ingest.inventory()`` and inspect the output, plus a manual
look at each distinct layout):

1. The exact column labels in every file/sheet, per year — verbatim,
   including casing, whitespace, and footnote markers.
2. Which sheet in each workbook holds the release-level records (vs.
   summary/notes sheets), and whether there are preamble rows above the
   header.
3. The observed dtypes and example values per column (dates as strings?
   Excel serials? hole size numeric or banded categories? units?).
4. The distinct values of every categorical column (severity, cause
   taxonomy and sub-categories, equipment type) per year, to define
   canonical category sets and spot drift across the OIR/9B → OIR12
   form changes.
5. How deliberate releases are flagged, if at all, and in which years.
6. Which years are present, which are missing, and whether any year
   spans multiple files or one file spans multiple years.

Every mapping decision goes in the Day 2 judgement-call table
(source column, target column, years affected, decision, rationale).
"""

from __future__ import annotations

#: Canonical column schema: {canonical_name: dtype_string}.
#: EMPTY until the real files are inspected — do not invent HSE columns.
#: TODO(Day 2): define canonical names and pandas dtypes from the real data.
CANONICAL_COLUMNS: dict[str, str] = {}

#: Year-to-source-column mapping: {year: {source_column_label: canonical_name}}.
#: One entry per reporting year (or per schema era, once eras are known).
#: EMPTY until the real files are inspected — do not invent HSE columns.
#: TODO(Day 2): fill from the inventory of real files.
YEAR_TO_SOURCE_COLUMNS: dict[int, dict[str, str]] = {}


def source_mapping_for_year(year: int) -> dict[str, str]:
    """Return the source→canonical column mapping for ``year``.

    Raises :class:`NotImplementedError` while the mapping table is empty,
    and :class:`KeyError` for a year absent from a populated table (a
    missing year is a data gap to document, not to paper over).
    """
    if not YEAR_TO_SOURCE_COLUMNS:
        raise NotImplementedError(
            "YEAR_TO_SOURCE_COLUMNS is empty. Needs: the real per-year column "
            "labels from data/raw/ (run hcr.ingest.inventory()) before any "
            "mapping can exist. See the module docstring for the full list."
        )
    return YEAR_TO_SOURCE_COLUMNS[year]
