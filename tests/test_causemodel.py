"""Tests for hcr.causemodel on a small synthetic corpus with a
learnable text→label signal."""

import pandas as pd
import pytest

pytest.importorskip("sklearn")

from hcr import causemodel  # noqa: E402

CORROSION_TEXTS = [
    "severe rust and corrosion found on pipework wall thinning observed",
    "external corrosion under insulation caused pinhole leak in line",
    "internal corrosion of carbon steel spool wall loss confirmed",
] * 8
NONE_TEXTS = [
    "valve left open during routine operations no equipment fault found",
    "operator opened wrong valve during lineup no equipment fault",
    "release during draining operations equipment intact and healthy",
] * 8


@pytest.fixture
def canonical() -> pd.DataFrame:
    texts = CORROSION_TEXTS + NONE_TEXTS
    labels = ["CORROSION"] * len(CORROSION_TEXTS) + ["NO EQUIPMENT FAILURE"] * len(
        NONE_TEXTS
    )
    # two unresolvable free-text rows + one label with no description
    texts += [
        "obvious rust damage and corrosion on the flange face",
        "valve left open",
        None,
    ]
    labels += ["Degradation of flange sealing", "Free text entry", "CORROSION"]
    return pd.DataFrame(
        {
            "record_id": [f"r{i}" for i in range(len(texts))],
            "description": texts,
            "equipment_failure_primary": labels,
        }
    )


def test_training_frame_selects_coded_rows_with_text(canonical):
    train = causemodel.training_frame(canonical)
    # excludes the two unresolvable labels and the description-less row
    assert len(train) == len(CORROSION_TEXTS) + len(NONE_TEXTS)
    assert set(train["equipment_failure_primary"]) == {
        "CORROSION",
        "NO EQUIPMENT FAILURE",
    }


def test_cross_validated_report_shapes(canonical):
    per_class, disagreements = causemodel.cross_validated_report(canonical, folds=3)
    assert set(per_class.columns) == {"class", "precision", "recall", "f1", "support"}
    overall = per_class.loc[per_class["class"] == "__overall__", "recall"].iloc[0]
    assert overall > 0.9  # separable synthetic corpus
    assert {"predicted", "confidence"} <= set(disagreements.columns)


def test_propose_for_unresolved_returns_worklist(canonical):
    proposals = causemodel.propose_for_unresolved(canonical)
    # both unresolvable rows have descriptions -> both get proposals
    assert len(proposals) == 2
    by_id = proposals.set_index("record_id")
    assert by_id.iloc[0]["confidence"] <= 1.0
    # the rust/corrosion free-text row should be proposed as CORROSION
    rust_id = canonical.iloc[-3]["record_id"]
    assert by_id.loc[rust_id, "proposed"] == "CORROSION"


def test_original_data_never_modified(canonical):
    before = canonical.copy()
    causemodel.propose_for_unresolved(canonical)
    pd.testing.assert_frame_equal(canonical, before)
