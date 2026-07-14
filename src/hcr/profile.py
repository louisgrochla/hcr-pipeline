"""Data-quality profiling: missingness, category drift, numeric
distributions.

Everything here returns DataFrames — no plotting, no visualisation
libraries (out of scope by design). Column names are parameters, so the
profilers are usable on raw or canonical data alike; nothing depends on
the not-yet-inspected HSE schema.
"""

from __future__ import annotations

import pandas as pd


def missingness_by_column_by_year(df: pd.DataFrame, year_column: str) -> pd.DataFrame:
    """Fraction of missing values per column, per year.

    Returns a DataFrame indexed by year with one column per input column
    (the year column itself excluded), values in [0, 1].
    """
    grouped = df.drop(columns=[year_column]).isna().groupby(df[year_column])
    return grouped.mean()


def category_drift(df: pd.DataFrame, column: str, year_column: str) -> pd.DataFrame:
    """Share of each category value per year, to expose drift over time
    (values appearing, disappearing, or renamed across reporting-form
    changes such as OIR/9B → OIR12).

    Returns a DataFrame indexed by year, one column per observed category
    value, rows summing to 1 (missing values counted as their own
    ``NaN`` category so drift in missingness is visible too).
    """
    counts = pd.crosstab(df[year_column], df[column], dropna=False)
    return counts.div(counts.sum(axis=1), axis=0)


def numeric_distribution(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Exact-value frequency table of a numeric column: ``value``,
    ``count``, ``share``, sorted by value.

    Exact values (not binned) on purpose: reporting artefacts show up as
    steps and spikes at round numbers that binning would smooth away —
    on ``hole_diameter_mm`` this exposes the 1mm round-down pile-up and
    the imperial-conversion spikes at 12.7/25.4mm. Quantified via
    :func:`boundary_concentration`; results in ``reports/profiling.md``.
    """
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    counts = values.value_counts().sort_index()
    return pd.DataFrame(
        {
            "value": counts.index,
            "count": counts.to_numpy(),
            "share": (counts / counts.sum()).to_numpy() if len(counts) else [],
        }
    ).reset_index(drop=True)


def boundary_concentration(
    df: pd.DataFrame,
    column: str,
    lower: float = 1.0,
    upper: float = 2.0,
) -> pd.DataFrame:
    """Quantify value pile-up at interval boundaries: counts and shares
    at exactly ``lower``, strictly between ``lower`` and ``upper``, and
    at exactly ``upper`` (shares relative to the three groups combined).

    Built for the known hole-size reporting artefact: reporters round
    hole diameters between 1mm and 2mm down to 1mm, so the exact-1mm
    count dwarfs the whole open interval (1, 2) — a step no smooth
    physical process produces. Works for any boundary pair (e.g. the
    imperial anchors 12.7mm and 25.4mm).
    """
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    counts = {
        f"= {lower}": int((values == lower).sum()),
        f"({lower}, {upper})": int(((values > lower) & (values < upper)).sum()),
        f"= {upper}": int((values == upper).sum()),
    }
    total = sum(counts.values())
    return pd.DataFrame(
        {
            "group": list(counts),
            "count": list(counts.values()),
            "share": [c / total if total else float("nan") for c in counts.values()],
        }
    )


def with_event_year(df: pd.DataFrame, date_column: str = "event_date") -> pd.DataFrame:
    """Return a copy with a ``year`` column derived from ``date_column``,
    for use as the ``year_column`` of the other profilers."""
    out = df.copy()
    out["year"] = pd.to_datetime(out[date_column], errors="coerce").dt.year
    return out
