# Analysis: cause-mix change in serious releases

## Question

**Which failure-cause dimensions are involved in offshore hydrocarbon
releases, and did the cause mix of serious releases change between
1999–2007 and 2008–2015?**

One question, bounded on purpose. The profiling (see
`reports/profiling.md`) rules out anything wider: severity is not
comparable across the 1999 criteria change, and the cause taxonomy is
not reliable after the 2016 form change.

## Method

Inclusion criteria (2,738 of 5,278 records):

- **Years 1999–2015**: after the severity-criteria refinement, within
  the coded-taxonomy era.
- **Process releases only** (`non_process == False`): diesel/lube-oil
  inventory releases are a different phenomenon.
- **Classified severity** (`MAJOR`, `SIGNIFICANT`, `MINOR`).

Definitions:

- A release "involves" a cause dimension when the corresponding field
  carries a positive value: `design_failure == 'FAILURE RELATED TO
  DESIGN'`; equipment/operational/procedural primary cause present and
  not its explicit `NO … FAILURE` value. Dimensions are not exclusive —
  43.8% of releases carry two or more (mean 1.55), so shares do not sum
  to 100%.
- Severity grouped as `MAJOR/SIGNIFICANT` (n=1,234) vs `MINOR`
  (n=1,504): major releases alone (n≈80) are too few for stable period
  splits.
- Periods split at 2007/2008, giving comparable spans (9 vs 8 years;
  n=1,834 vs 904).

Reproducible with the package alone:

```python
import pandas as pd
from hcr import ingest, clean, profile

df = pd.concat(
    [clean.clean_records(t["frame"], year=t["years"][0])
     for t in ingest.load_source_tables()],
    ignore_index=True,
)
a = profile.with_event_year(df)
a = a[a["year"].between(1999, 2015)
      & ~a["non_process"].fillna(False)
      & a["severity"].isin({"MAJOR", "SIGNIFICANT", "MINOR"})].copy()
a["design"] = a["design_failure"].eq("FAILURE RELATED TO DESIGN")
for dim in ["equipment", "operational", "procedural"]:
    col = f"{dim}_failure_primary" if dim != "equipment" else "equipment_failure_primary"
    a[dim] = a[col].notna() & ~a[col].isin({f"NO {dim.upper()} FAILURE"})
a["sev2"] = a["severity"].map(
    lambda s: "MAJOR/SIGNIFICANT" if s in {"MAJOR", "SIGNIFICANT"} else "MINOR")
a["period"] = pd.cut(a["year"], [1998, 2007, 2015],
                     labels=["1999-2007", "2008-2015"])
a.groupby(["period", "sev2"], observed=True)[
    ["design", "equipment", "operational", "procedural"]].mean()
```

## Results

Cause-dimension involvement, share of releases:

| period | severity | design | equipment | operational | procedural |
|---|---|---|---|---|---|
| 1999–2007 | MAJOR/SIGNIFICANT (n=832) | 0.149 | 0.725 | 0.468 | 0.240 |
| 1999–2007 | MINOR (n=1,002) | 0.122 | 0.728 | 0.420 | 0.203 |
| 2008–2015 | MAJOR/SIGNIFICANT (n=402) | 0.158 | 0.699 | **0.550** | **0.331** |
| 2008–2015 | MINOR (n=502) | 0.092 | 0.739 | 0.432 | 0.241 |

## Finding

Equipment failure is the dominant cause dimension throughout (~70–74%)
and is stable across periods and severities. The change is in the
human-and-organisational dimensions, and it is concentrated in the
serious releases: for MAJOR/SIGNIFICANT events, operational involvement
rose from 46.8% to 55.0% (difference ≈ 2.7 standard errors of a
two-proportion comparison) and procedural involvement from 24.0% to
33.1% (≈ 3.3 SE), while the same shares for MINOR releases moved only
1–4 points. Reported serious releases in 2008–2015 were, relative to
the previous period, materially more likely to have an operational or
procedural failure recorded alongside the equipment cause.

## What this does and does not say

- It describes *recorded causes in a voluntary register*, not incidence:
  a shift in investigation or coding practice (e.g. more willingness to
  record human factors after the 2005–2010 KP3 asset-integrity
  scrutiny period) would produce the same signature. The data cannot
  distinguish these.
- Total reporting volume fell across the same span (~250/yr → ~120/yr),
  so shares, not counts, are compared.
- No causal claim, no extrapolation past 2015: the post-2016 cause
  fields are free text with ~17% unresolvable entries
  (`reports/schema_mapping.md`) and cannot support this comparison.
