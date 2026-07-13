"""Validation rules for the cleaned HCR data.

Every rule is a named function that returns the **DataFrame of failing
rows** — never a bare boolean. An empty result means the rule passed.

Two layers:

* Generic, schema-independent rule primitives (implemented and tested
  now) that take column names and limits as arguments.
* Named HCR rules (hole size, severity, date, cause) that will bind the
  primitives to the canonical schema — blocked on Day 2, so they raise
  :class:`NotImplementedError` stating what they need. ``run_all``
  records blocked rules in its summary rather than crashing: gaps are
  documented, not fatal.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import pandas as pd

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
# Named HCR rules — blocked on the Day 2 schema
# ---------------------------------------------------------------------------


def hole_size_within_plausible_bounds(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: hole size outside plausible physical bounds.

    Blocked: needs the canonical hole-size column name, its units as
    reported by HSE, and agreed plausible bounds — then delegates to
    :func:`numeric_within_bounds`.
    """
    raise NotImplementedError(
        "Needs from the real data: canonical hole-size column name, units, "
        "and agreed plausible bounds (schema.py, Day 2). Implement via "
        "numeric_within_bounds()."
    )


def severity_in_permitted_set(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: severity not in the permitted set.

    Blocked: needs the canonical severity column name and the exact
    permitted values as they appear in the real files (expected to be a
    major/significant/minor taxonomy, but the literal strings must come
    from the data, not be invented) — then delegates to
    :func:`values_in_set`.
    """
    raise NotImplementedError(
        "Needs from the real data: canonical severity column name and the "
        "exact observed severity values per year (schema.py, Day 2). "
        "Implement via values_in_set()."
    )


def date_within_reporting_period(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: release date outside the reporting period
    (collection began October 1992; the end bound depends on the latest
    published year).

    Blocked: needs the canonical date column name, the raw date encoding,
    and the end of the covered period from the downloaded files — then
    delegates to :func:`dates_within_period`.
    """
    raise NotImplementedError(
        "Needs from the real data: canonical date column name, its raw "
        "encoding, and the last covered reporting date in the downloaded "
        "files (schema.py, Day 2). Implement via dates_within_period()."
    )


def cause_category_resolvable(df: pd.DataFrame) -> pd.DataFrame:
    """Failing rows: cause category not resolvable in the cause taxonomy.

    Blocked: needs the canonical cause column name(s) and the real
    taxonomy values (design / equipment / operation / procedural
    sub-categories as actually spelled in the files) — then delegates to
    :func:`values_in_set`.
    """
    raise NotImplementedError(
        "Needs from the real data: canonical cause column name(s) and the "
        "observed taxonomy values per year (schema.py, Day 2). Implement "
        "via values_in_set()."
    )


#: Default rule registry for run_all(). Blocked rules stay listed so the
#: summary shows them as blocked instead of silently omitting them.
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
