"""Validation rules for the cleaned HCR data.

Every rule is a named function that returns the **DataFrame of failing
rows** — never a bare boolean. An empty result means the rule passed.

Two layers:

* Generic, schema-independent rule primitives that take column names
  and limits as arguments.
* Named HCR rules (hole size, severity, date, cause) binding the
  primitives to the canonical schema (:mod:`hcr.schema`). They expect a
  frame cleaned by :func:`hcr.clean.clean_records`. ``run_all`` records
  any rule that raises :class:`NotImplementedError` as ``blocked``
  rather than crashing: gaps are documented, not fatal.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import pandas as pd

from hcr import schema

Rule = Callable[[pd.DataFrame], pd.DataFrame]


# ---------------------------------------------------------------------------
# Generic rule primitives — implemented now
# ---------------------------------------------------------------------------


def numeric_within_bounds(
    df: pd.DataFrame,
    column: str,
    lower: float | None = None,
    upper: float | None = None,
) -> pd.DataFrame:
    """Rows where ``column`` is non-numeric, missing, or outside
    ``[lower, upper]`` (bounds inclusive; ``None`` means unbounded).
    """
    values = pd.to_numeric(df[column], errors="coerce")
    failing = values.isna()
    if lower is not None:
        failing |= values < lower
    if upper is not None:
        failing |= values > upper
    return df.loc[failing]


def values_in_set(df: pd.DataFrame, column: str, allowed: set) -> pd.DataFrame:
    """Rows where ``column`` is missing or not in ``allowed``."""
    return df.loc[~df[column].isin(allowed) | df[column].isna()]


def dates_within_period(
    df: pd.DataFrame,
    column: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Rows where ``column`` is not parseable as a date or falls outside
    ``[start, end]`` (inclusive).
    """
    dates = pd.to_datetime(df[column], errors="coerce")
    failing = dates.isna() | (dates < pd.Timestamp(start)) | (dates > pd.Timestamp(end))
    return df.loc[failing]


def no_duplicate_keys(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """Rows involved in a duplicate on ``subset`` (all occurrences
    returned, so the collision is visible, not just the second copy).
    """
    return df.loc[df.duplicated(subset=subset, keep=False)]


# ---------------------------------------------------------------------------
# Named HCR rules — bound to the canonical schema (see hcr.schema and
# reports/schema_mapping.md for where every constant was observed)
# ---------------------------------------------------------------------------


def hole_size_within_plausible_bounds(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: ``hole_diameter_mm`` present but implausible —
    non-positive, or above the largest genuine observed value (1000 mm).

    Missing values do **not** fail this rule: after cleaning, NA covers
    both true gaps and era 2's free-text entries (``'1mm'``, ``'<5'``
    …), and missingness is quantified separately by
    :func:`hcr.profile.missingness_by_column_by_year`. The era-1 ``999``
    unknown-size code is expected to have been converted to NA by
    :func:`hcr.clean.replace_missing_value_codes`; if it survives, it
    fails here (999 < 1000 is false — it exceeds no bound — so the
    sentinel must be handled in cleaning, which is deliberate: this rule
    checks physical plausibility, not encoding).
    """
    lower, upper = schema.HOLE_DIAMETER_PLAUSIBLE_MM
    values = pd.to_numeric(df["hole_diameter_mm"], errors="coerce")
    failing = values.notna() & ((values <= lower) | (values > upper))
    return df.loc[failing]


def severity_in_permitted_set(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: ``severity`` missing or outside the permitted set
    observed in the files ({MAJOR, SIGNIFICANT, MINOR, AWAITING
    CLASSIFICATION}, compared after category normalisation).

    Missing **does** fail here: every release record is supposed to
    carry a classification (pre-1997 rows were classified
    retroactively), so an absent severity is a defect of the record.
    The one era-1 row with severity ``'NON-PROCESS'`` fails by design.
    """
    return values_in_set(df, "severity", schema.SEVERITY_PERMITTED)


def date_within_reporting_period(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: ``event_date`` missing, unparseable, or outside the
    official reporting period (1 Oct 1992 – 31 Dec 2021).

    The known era-1 record dated 1992-09-26 fails by design — it
    predates the official start of collection and is a finding for the
    data-quality report, not something to silently accept.
    """
    start, end = schema.REPORTING_PERIOD
    return dates_within_period(df, "event_date", start=start, end=end)


def cause_category_resolvable(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: any cause field present but not resolvable in the
    coded taxonomy (era 1's closed sets, see ``schema.CAUSE_TAXONOMY``).

    Missing cause fields do not fail (missingness is profiled
    separately); a *populated* field that doesn't resolve does. Era 2 is
    known to be free-text contaminated, so its failure count here is a
    measurement of that contamination — expected to be large, and
    that's the finding.
    """
    failing = pd.Series(False, index=df.index)
    for column, allowed in schema.CAUSE_TAXONOMY.items():
        present = df[column].notna()
        failing |= present & ~df[column].isin(allowed)
    return df.loc[failing]


#: Default rule registry for run_all(), keyed by rule name.
DEFAULT_RULES: dict[str, Rule] = {
    "hole_size_within_plausible_bounds": hole_size_within_plausible_bounds,
    "severity_in_permitted_set": severity_in_permitted_set,
    "date_within_reporting_period": date_within_reporting_period,
    "cause_category_resolvable": cause_category_resolvable,
}


def run_all(
    df: pd.DataFrame,
    rules: Mapping[str, Rule] | None = None,
) -> pd.DataFrame:
    """Run every rule and return a summary DataFrame with one row per
    rule: ``rule``, ``status`` (``ok`` / ``blocked``), ``n_failing``,
    ``n_rows``, ``pass_rate``.

    A rule that raises :class:`NotImplementedError` is recorded as
    ``blocked`` (with NaN counts) rather than aborting the run — the
    pipeline documents gaps and moves on.
    """
    if rules is None:
        rules = DEFAULT_RULES
    n_rows = len(df)
    records = []
    for name, rule in rules.items():
        try:
            failing = rule(df)
        except NotImplementedError:
            records.append(
                {
                    "rule": name,
                    "status": "blocked",
                    "n_failing": None,
                    "n_rows": n_rows,
                    "pass_rate": None,
                }
            )
            continue
        n_failing = len(failing)
        records.append(
            {
                "rule": name,
                "status": "ok",
                "n_failing": n_failing,
                "n_rows": n_rows,
                "pass_rate": 1.0 - n_failing / n_rows if n_rows else None,
            }
        )
    return pd.DataFrame.from_records(
        records, columns=["rule", "status", "n_failing", "n_rows", "pass_rate"]
    )
