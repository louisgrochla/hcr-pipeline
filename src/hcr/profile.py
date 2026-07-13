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
    steps and spikes at round numbers that binning would smooth away.

    TODO(Day 5): run this on the hole-size column once the schema is
    mapped — the known artefact to quantify is under-reporting of hole
    sizes between 1mm and 2mm because reporters round down, visible as a
    step in this distribution.
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
