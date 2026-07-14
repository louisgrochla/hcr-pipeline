# Can the incident narrative recover the cause code? (A negative result)

## Question

The register's cause taxonomy degrades into free text after 2016
(`schema_mapping.md`: a residual of unresolvable entries even after
conservative consolidation). The obvious proposed fix is supervised
text classification: train on era 1, where 3,190 records carry both a
free-text narrative and a human-assigned cause code, and predict codes
for the broken era-2 entries.

**Tested. It does not work — and the number says something useful.**

## Method

TF-IDF (word 1–2-grams) + class-balanced logistic regression
(`hcr.causemodel`), 5-fold out-of-fold evaluation on the era-1 labelled
set (`description` → cause code). Deliberately simple and inspectable;
the point is to measure whether the signal exists at all.

## Results

| target | n | model accuracy | majority baseline | lift |
|---|---|---|---|---|
| equipment_failure_primary (6 classes) | 3,190 | 0.470 | 0.424 | +0.046 |
| equipment failure — binary (any vs none) | 3,190 | 0.724 | 0.686 | +0.039 |
| operational_failure_primary | 3,179 | 0.419 | 0.509 | −0.090 |
| procedural_failure_primary | 3,194 | 0.621 | 0.717 | −0.096 |
| design_failure (2 classes) | 3,242 | 0.793 | 0.871 | −0.078 |

(The negative lifts are the class-balanced model trading majority-class
accuracy for minority recall — even so, nothing here approaches usable
recovery quality. Per-class F1 for the best target tops out at 0.58.)

## Interpretation

The narrative describes **what happened**; the cause code records **why
it happened**, which the human coder took from the investigation, not
from the narrative. Example of the gap: a description of gas migrating
into a drains system reads as "no equipment failure" to the model, but
the coder — who knew a blocked LP vent caused it — coded MECHANICAL.
The information needed to code causes is largely *not in the text*.

Consequences:

1. **Era 2's broken cause fields cannot be repaired from the
   descriptions alone.** Restoring them would need the underlying
   OIR/12 investigation detail, which is not in the public data. The
   ~17% unresolvable residual should be treated as permanent.
2. **The coded taxonomy was carrying real, independent information** —
   exactly why its post-2016 loss matters. If the codes were mere
   summaries of the narratives, losing them would be cosmetic; they
   weren't, so it isn't.
3. The disagreement set is dominated by model uncertainty (no
   out-of-fold disagreement reaches 0.6 confidence), so it cannot be
   read as a label-noise audit of the human coders — an honest limit of
   this data, stated rather than glossed.

## Reproduce

```python
import pandas as pd
from hcr import ingest, clean, causemodel

df = pd.concat(
    [clean.clean_records(t["frame"], year=t["years"][0])
     for t in ingest.load_source_tables()],
    ignore_index=True,
)
per_class, disagreements = causemodel.cross_validated_report(df)
proposals = causemodel.propose_for_unresolved(df)   # review worklist, low confidence
```

Requires the `nlp` extra (`pip install -e ".[nlp]"`).
