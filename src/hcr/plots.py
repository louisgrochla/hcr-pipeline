"""Figures for the data-quality report.

Static matplotlib renderings of the three headline profiling findings.
Every function takes the cleaned canonical frame (see
:func:`hcr.clean.clean_records`), draws from :mod:`hcr.profile` numbers,
and returns a :class:`matplotlib.figure.Figure`; :func:`save_all` writes
them as PNGs under ``reports/figures/``.

Requires matplotlib (in the ``dev`` extra): ``pip install -e ".[dev]"``.
Uses the object-oriented API only — no pyplot state, no backend needed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from matplotlib.figure import Figure
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        'hcr.plots needs matplotlib; install the dev extras: pip install -e ".[dev]"'
    ) from exc

from hcr import profile

# Validated categorical palette (fixed slot order) and text/surface tokens.
BLUE = "#2a78d6"
AQUA = "#1baf7a"
YELLOW = "#eda100"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e5e4e0"
SURFACE = "#fcfcfb"


def _base_axes(fig: Figure, title: str, subtitle: str):
    """One consistent frame: recessive grid, no top/right spines,
    title/subtitle in text tokens (never series colors)."""
    ax = fig.subplots()
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.suptitle(title, x=0.02, ha="left", fontsize=13, color=TEXT, fontweight="bold")
    ax.set_title(subtitle, loc="left", fontsize=10, color=TEXT_2, pad=12)
    return ax


def hole_size_distribution(df: pd.DataFrame) -> Figure:
    """The round-down artefact: exact-value counts of
    ``hole_diameter_mm`` up to 30mm. The 1mm spike against the empty
    (1, 2)mm valley is the finding; imperial anchors are called out."""
    nd = profile.numeric_distribution(df, "hole_diameter_mm")
    nd = nd[nd["value"] <= 30]
    fig = Figure(figsize=(9, 4.4), dpi=200, layout="constrained")
    ax = _base_axes(
        fig,
        "Reporters round hole sizes down",
        "Count of releases at each exact equivalent hole diameter, 0–30 mm, 1992–2021",
    )
    ax.bar(nd["value"], nd["count"], width=0.22, color=BLUE)
    one = int(nd.loc[nd["value"] == 1.0, "count"].sum())
    between = int(nd.loc[(nd["value"] > 1) & (nd["value"] < 2), "count"].sum())
    ax.annotate(
        f"exactly 1 mm: {one:,} releases —\nmore than the whole 1–2 mm interval "
        f"({between}) combined",
        xy=(1.0, one),
        xytext=(3.2, one * 0.86),
        fontsize=9,
        color=TEXT,
        arrowprops={"arrowstyle": "-", "color": TEXT_2, "linewidth": 0.8},
    )
    for mm, inches in [(6.35, '¼"'), (12.7, '½"'), (25.4, '1"')]:
        count = int(nd.loc[nd["value"] == mm, "count"].sum())
        ax.annotate(
            f"{inches}\n({mm} mm)",
            xy=(mm, count),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=TEXT_2,
        )
    ax.set_xlabel("equivalent hole diameter (mm)", fontsize=9, color=TEXT_2)
    ax.set_ylabel("releases", fontsize=9, color=TEXT_2)
    ax.set_xlim(-0.5, 30.5)
    return fig


def measurement_missingness(df: pd.DataFrame) -> Figure:
    """The era-2 measurement collapse: fraction of records per year with
    unusable hole-size / released-quantity values."""
    dfy = profile.with_event_year(df)
    miss = profile.missingness_by_column_by_year(
        dfy[["hole_diameter_mm", "quantity_released_kg", "year"]], "year"
    )
    fig = Figure(figsize=(9, 4.2), dpi=200, layout="constrained")
    ax = _base_axes(
        fig,
        "The register's measurements are degrading",
        "Fraction of releases per year with missing or unparseable values",
    )
    ax.plot(miss.index, miss["quantity_released_kg"], color=BLUE, linewidth=2)
    ax.plot(miss.index, miss["hole_diameter_mm"], color=AQUA, linewidth=2)
    ax.axvline(2015.5, color=GRID, linewidth=1.2)
    ax.annotate(
        "2016 form change",
        xy=(2015.5, 0.55),
        ha="right",
        fontsize=8,
        color=TEXT_2,
        xytext=(-4, 0),
        textcoords="offset points",
    )
    last = miss.index.max()
    ax.annotate(
        f"quantity released: {miss.loc[last, 'quantity_released_kg']:.0%} missing "
        f"by {int(last)}",
        xy=(last, miss.loc[last, "quantity_released_kg"]),
        xytext=(-6, 6),
        textcoords="offset points",
        ha="right",
        fontsize=9,
        color=TEXT,
        fontweight="bold",
    )
    ax.annotate(
        "hole diameter",
        xy=(last, miss.loc[last, "hole_diameter_mm"]),
        xytext=(-6, 8),
        textcoords="offset points",
        ha="right",
        fontsize=9,
        color=TEXT,
    )
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("fraction missing", fontsize=9, color=TEXT_2)
    return fig


def severity_drift(df: pd.DataFrame) -> Figure:
    """The 1999 classification step: yearly share of each severity
    class. The MINOR/SIGNIFICANT flip at 1999 is a criteria artefact."""
    dfy = profile.with_event_year(df)
    drift = profile.category_drift(dfy, "severity", "year")
    fig = Figure(figsize=(9, 4.2), dpi=200, layout="constrained")
    ax = _base_axes(
        fig,
        "Severity classes are not comparable across 1999",
        "Share of releases per year by severity classification",
    )
    series = [("MINOR", BLUE), ("SIGNIFICANT", AQUA), ("MAJOR", YELLOW)]
    for name, color in series:
        ax.plot(drift.index, drift[name], color=color, linewidth=2)
        ax.annotate(
            name,
            xy=(drift.index.max(), drift[name].iloc[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=9,
            color=TEXT,
            va="center",
        )
    ax.axvline(1998.5, color=GRID, linewidth=1.2)
    ax.annotate(
        "1999 criteria refinement",
        xy=(1998.5, 0.93),
        fontsize=8,
        color=TEXT_2,
        xytext=(4, 0),
        textcoords="offset points",
    )
    awaiting = drift.get("AWAITING CLASSIFICATION")
    if awaiting is not None and awaiting.iloc[-1] > 0.05:
        ax.annotate(
            f"2021 is provisional: {awaiting.iloc[-1]:.0%} of its releases still "
            "awaited classification (not shown)",
            xy=(drift.index.max() - 1, 0.08),
            ha="right",
            fontsize=8,
            color=TEXT_2,
        )
    ax.set_ylim(0, 1.0)
    ax.set_xlim(drift.index.min(), drift.index.max() + 4)
    ax.set_ylabel("share of releases", fontsize=9, color=TEXT_2)
    return fig


def save_all(df: pd.DataFrame, outdir: Path | str = "reports/figures") -> list[Path]:
    """Render every figure to PNG under ``outdir``; returns the paths."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    figures = {
        "hole_size_distribution.png": hole_size_distribution,
        "measurement_missingness.png": measurement_missingness,
        "severity_drift.png": severity_drift,
    }
    paths = []
    for name, fn in figures.items():
        path = outdir / name
        fn(df).savefig(path, facecolor=SURFACE)
        paths.append(path)
    return paths
