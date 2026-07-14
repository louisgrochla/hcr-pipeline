"""Smoke tests for hcr.plots: figures render and save from a small
synthetic canonical frame (no real data needed)."""

import pandas as pd
import pytest

matplotlib = pytest.importorskip("matplotlib")

from hcr import plots  # noqa: E402


@pytest.fixture
def canonical() -> pd.DataFrame:
    years = list(range(1993, 2021)) * 3
    n = len(years)
    return pd.DataFrame(
        {
            "event_date": pd.to_datetime([f"{y}-06-01" for y in years]),
            "hole_diameter_mm": ([1.0, 1.5, 12.7] * n)[:n],
            "quantity_released_kg": ([10.0, None, 3.0] * n)[:n],
            "severity": (["MINOR", "SIGNIFICANT", "MAJOR"] * n)[:n],
        }
    )


def test_each_figure_renders(canonical):
    for fn in (
        plots.hole_size_distribution,
        plots.measurement_missingness,
        plots.severity_drift,
    ):
        fig = fn(canonical)
        assert fig.axes, fn.__name__


def test_save_all_writes_pngs(canonical, tmp_path):
    paths = plots.save_all(canonical, outdir=tmp_path)
    assert len(paths) == 3
    for p in paths:
        assert p.exists() and p.stat().st_size > 0
