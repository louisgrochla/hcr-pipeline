# Data-quality profiling — Day 5

All numbers computed on the cleaned canonical dataset (5,278 records,
1992–2021) with the `hcr.profile` functions:

```python
import pandas as pd
from hcr import ingest, clean, profile

df = pd.concat(
    [clean.clean_records(t["frame"], year=t["years"][0])
     for t in ingest.load_source_tables()],
    ignore_index=True,
)
dfy = profile.with_event_year(df)
```

## 1. The hole-size rounding artefact — confirmed and quantified

`profile.boundary_concentration(dfy, "hole_diameter_mm", 1.0, 2.0)`:

| group | count | share |
|---|---|---|
| exactly 1.0 mm | 1,043 | **60.5%** |
| strictly between 1 and 2 mm | 441 | 25.6% |
| exactly 2.0 mm | 240 | 13.9% |

Of every release whose equivalent hole diameter lies in [1, 2] mm,
three in five are recorded as exactly 1.0 mm. No smooth physical
process produces a step like that: reporters round down. Any leak-size
frequency analysis (e.g. QRA failure-rate curves) that treats these as
true 1 mm holes systematically understates hole size in the 1–2 mm
band.

The exact-value distribution (`profile.numeric_distribution`) also
shows imperial-conversion spikes — reporters working in inches:

| value (mm) | = inches | count |
|---|---|---|
| 6.35 | ¼″ | 55 |
| 12.70 | ½″ | 105 |
| 25.40 | 1″ | 58 |
| 50.80 | 2″ | 47 |

12.7 mm is the 7th most common exact value in the entire register.
Hole sizes are therefore a mixture of two measurement cultures (metric
round numbers and converted imperial), plus the 1 mm pile-up.

## 2. Missingness by column by year

`profile.missingness_by_column_by_year` — fraction missing, era-level
summary of the canonical core:

| column | era 1 (1992–2015) | era 2 (2016–2021) |
|---|---|---|
| hole_diameter_mm | 0.036 | **0.203** |
| quantity_released_kg | 0.000 | **0.391** |
| severity | 0.000 | 0.000 |
| system_primary | 0.002 | 0.023 |
| equipment_primary | 0.065 | 0.090 |
| equipment_failure_primary | 0.001 | 0.080 |
| operational_failure_primary | 0.001 | 0.079 |
| procedural_failure_primary | 0.002 | **0.145** |
| operational_mode_primary | 0.003 | 0.096 |
| ignition_occurred | 0.000 | 0.006 |

Two caveats on reading this: era-2 "missing" for `hole_diameter_mm`
includes free-text entries (`'1mm'`, `'<5'`, ranges) that could not be
coerced to numbers — the raw cells are populated but unusable; and
era-1 near-zero missingness partly reflects that the old workflow
technically checked OIR/12 returns against RIDDOR.

**The sharpest finding is the year-on-year collapse of
`quantity_released_kg` inside era 2:**

| year | fraction missing |
|---|---|
| 2016 | 0.000 |
| 2017 | 0.009 |
| 2018 | 0.020 |
| 2019 | **0.672** |
| 2020 | **0.755** |
| 2021 | **0.912** |

Released-quantity data effectively stops being usable from 2019. Hole
size in 2021 is also 39.6% missing. The register's physical-measurement
content is degrading, not just its taxonomy.

## 3. Severity drift: the 1999 classification step

Severity shares by period (`profile.category_drift` aggregated;
criteria first introduced 1997, refined 1999 to include release rates —
per the file's own Introduction):

| period | MAJOR | SIGNIFICANT | MINOR | AWAITING |
|---|---|---|---|---|
| 1992–96 (retro-classified) | 0.089 | 0.585 | 0.325 | — |
| 1997–98 | 0.057 | 0.611 | 0.331 | — |
| 1999–2015 | 0.029 | 0.394 | 0.576 | 0.001 |
| 2016–21 | 0.021 | 0.341 | 0.566 | 0.072 |

The MINOR/SIGNIFICANT ratio flips at 1999 (33%/59% → 58%/39%). That is
a reclassification artefact, not a change in the world: severity trends
must not be computed across the 1999 boundary without acknowledging it.
7.2% of era-2 records (concentrated in provisional 2021: 45 of 91) are
still `AWAITING CLASSIFICATION`.

## 4. Category drift at the 2016 era boundary

Distinct values per column (after cleaning and synonym consolidation):

| column | era 1 | era 2 | pattern |
|---|---|---|---|
| equipment_failure_primary | 6 | 24 | closed 6-value code list replaced by free text; new recurring concepts (`DEGRADATION OF VALVE SEALING` 23, `LOSS OF BOLT TENSIONING` 10) have no era-1 home |
| operational_mode_primary | 10 | 29 | era-1 compound buckets (`FLUSHING/CLEANING/INSPECTION`, `TESTING/SAMPLING`) split into finer values (`STARTUP` 39, `PLANNED MAINTENANCE` 33, well ops with/without tree) |
| system_primary | 19 | 25 | mostly stable; residual spelling drift consolidated in the synonym table |

Direction of drift: granularity increased after 2016, but discipline
collapsed — the finer categories arrive as free text with typos and
sentence-length entries (quantified in `reports/schema_mapping.md`:
107 unresolvable cause entries remain after conservative recovery).

## 5. Coverage shape

Releases per year: 1992 has 40 records (collection started 1 October —
a quarter-year, not a low-incident year; annualising 1992 without
correction understates nothing but *including it raw in yearly trends
does*). Reporting declines from ~270/yr (early 2000s) to ~90–130/yr
(2012 onwards) with no gap years. 2021 is provisional.

## Implications for downstream analysis

1. Exclude or correct 1992 in any per-year rate; it is 3 months.
2. Do not compare severity mixes across 1999.
3. Do not use `quantity_released_kg` after 2018.
4. Treat 1–2 mm hole sizes as a rounded band, not point values.
5. Era-2 cause analysis is only ~83% covered even after recovery
   (free text + missingness); state coverage alongside any result.
