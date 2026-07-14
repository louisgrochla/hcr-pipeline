"""Recovering cause categories from incident free text.

The post-2016 reporting regime lost the coded cause taxonomy (see
``reports/schema_mapping.md``): a residual of cause entries is
unrecoverable free text. This module asks the follow-up question — can
the *incident narrative* predict the cause code well enough to (a)
audit the human coding and (b) propose codes for the unresolvable rows?

Approach, deliberately small: TF-IDF over the ``description`` field +
logistic regression, trained on era-1 records where a human coder
assigned a taxonomy value. No deep learning, no external data. All
outputs are *proposals with probabilities*, never silent fixes — the
cleaned dataset is untouched by this module.

Requires scikit-learn (``pip install -e ".[nlp]"`` or the dev extras).
"""

from __future__ import annotations

import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict
    from sklearn.pipeline import Pipeline
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "hcr.causemodel needs scikit-learn; install the nlp extras: "
        'pip install -e ".[nlp]"'
    ) from exc

from hcr import schema

#: Default target: the cause column with the largest unrecoverable
#: residual and a clean 6-value era-1 code list.
DEFAULT_TARGET = "equipment_failure_primary"


def training_frame(df: pd.DataFrame, target: str = DEFAULT_TARGET) -> pd.DataFrame:
    """Rows usable for supervised training: non-empty ``description``
    and a ``target`` value inside the coded era-1 taxonomy.

    In practice this selects era-1 records (era-2 labels are largely
    free text and get excluded by the taxonomy test); the description
    style therefore differs between training (era-1 ``Comments``) and
    application (era-2 narratives) — a domain shift that is reported,
    not hidden.
    """
    allowed = schema.CAUSE_TAXONOMY[target]
    mask = (
        df["description"].notna()
        & (df["description"].astype(str).str.strip() != "")
        & df[target].isin(allowed)
    )
    return df.loc[mask, ["record_id", "description", target]]


def build_model() -> Pipeline:
    """The classifier: word 1–2-gram TF-IDF into a class-balanced
    logistic regression. Small, fast, and linear — every prediction is
    inspectable via its coefficients."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=3,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0),
            ),
        ]
    )


def cross_validated_report(
    df: pd.DataFrame, target: str = DEFAULT_TARGET, folds: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Out-of-fold evaluation on the labelled data.

    Returns ``(per_class, disagreements)``:

    * ``per_class`` — precision/recall/F1/support per taxonomy value,
      plus an ``__overall__`` row (accuracy in the recall column).
    * ``disagreements`` — every labelled row whose out-of-fold
      prediction differs from the human code, with the model's
      confidence. High-confidence disagreements are label-noise
      candidates: places where the narrative reads like one category
      but the coder chose another.
    """
    train = training_frame(df, target)
    model = build_model()
    predicted = cross_val_predict(model, train["description"], train[target], cv=folds)
    proba = cross_val_predict(
        model, train["description"], train[target], cv=folds, method="predict_proba"
    )
    confidence = proba.max(axis=1)

    rows = []
    y = train[target]
    for cls in sorted(y.unique()):
        tp = ((predicted == cls) & (y == cls)).sum()
        fp = ((predicted == cls) & (y != cls)).sum()
        fn = ((predicted != cls) & (y == cls)).sum()
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        rows.append(
            {
                "class": cls,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": int((y == cls).sum()),
            }
        )
    rows.append(
        {
            "class": "__overall__",
            "precision": float("nan"),
            "recall": (predicted == y).mean(),
            "f1": float("nan"),
            "support": len(y),
        }
    )
    per_class = pd.DataFrame(rows)

    disagreements = train.loc[predicted != y].copy()
    disagreements["predicted"] = predicted[predicted != y]
    disagreements["confidence"] = confidence[predicted != y]
    disagreements = disagreements.sort_values("confidence", ascending=False)
    return per_class, disagreements


def propose_for_unresolved(
    df: pd.DataFrame, target: str = DEFAULT_TARGET
) -> pd.DataFrame:
    """Fit on all labelled rows, then propose taxonomy codes for rows
    whose ``target`` is present but unresolvable (era 2's free-text
    residue) and which carry a description.

    Returns record_id, the unresolvable original value, the proposed
    code and the model's confidence — a review worklist, not an
    auto-fix.
    """
    train = training_frame(df, target)
    model = build_model()
    model.fit(train["description"], train[target])

    allowed = schema.CAUSE_TAXONOMY[target]
    mask = (
        df[target].notna()
        & ~df[target].isin(allowed)
        & df["description"].notna()
        & (df["description"].astype(str).str.strip() != "")
    )
    unresolved = df.loc[mask, ["record_id", "description", target]].copy()
    if unresolved.empty:
        return unresolved.assign(
            proposed=pd.Series(dtype=str), confidence=pd.Series(dtype=float)
        )
    proba = model.predict_proba(unresolved["description"])
    unresolved["proposed"] = model.classes_[proba.argmax(axis=1)]
    unresolved["confidence"] = proba.max(axis=1)
    return unresolved.sort_values("confidence", ascending=False)
