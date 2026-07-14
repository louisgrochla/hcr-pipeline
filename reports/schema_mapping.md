# Schema mapping and judgement calls — Day 2

Canonical schema: `src/hcr/schema.py`. Every decision below traces to
the inspected files (`reports/inventory.md`). Source labels are quoted
verbatim — trailing spaces, embedded newlines (`\n`) and misspellings
included, because the mapping must match the files exactly.

Eras: **1** = `hsr1992–2014.xlsx::Results` (1992–2015, header row 1),
**2** = `hcr2016-2021.xlsx::HCRs <year> Final/Provisional` (2016–2021,
header row 0).

## Column mapping

| Canonical | Era 1 source | Era 2 source | Decision / rationale |
|---|---|---|---|
| `record_id` | `HCRDID` | `URN` | Both unique & non-null (era 2: after dropping padding rows). Dedup key. |
| `event_date` | `Incident Date` | `Event Date` | True Excel datetimes in both eras; fiscal/calendar year columns dropped as derivable. |
| `severity` | `Severity` | `Severity classification of this release\n(classified by HSL)` | Newline in era-2 label is genuine. |
| `hole_diameter_mm` | `Equivalent hole diameter [mm]` | same label | Same label both eras. Era 1: numeric with `999` unknown-code. Era 2: numeric mixed with free text (`'1mm'`, `'<5'`, `'1.00 - 2.00'`, `'Two holes: 10mm and 5mm'`) — free text coerces to NA, loss quantified in profiling. |
| `quantity_released_kg` | `Estimated quantity released (kg) ` (trailing space) | `Estimated quantity released (KG) (converted by HSL)` | Era 2 also has `(supplied by DH)` variant; the HSL-converted kg column is chosen as the comparable unit. |
| `system_primary/…/quaternary` | `System Primary` … `System Quarternary` (sic) | `System Primary` … `System Quaternary` | Era 1 misspells "Quarternary"; canonical uses the correct spelling. |
| `equipment_primary/…/tertiary` | `Equipment Primary` … | same labels | Direct match. Era-1 `Equipment Code`/era-2 `Equipment: Other` not mapped (era-specific). |
| `design_failure` | `Design Cause` | `Design Failure related to Design?` | Era 1's redundant yes/no `Was there a Design Failure?` dropped; `Design Cause` values (`FAILURE RELATED TO DESIGN` / `NO DESIGN FAILURE`) align with era 2's column (where not free-text). |
| `equipment_failure_primary/secondary` | `Equipment Failure Primary/Secondary` | same labels | Direct match. |
| `operational_failure_primary/secondary` | `Operational Failure Primary` / `Operational failure Secondary` | same labels | Era 1 yes/no `Was there an operational cause?` dropped (implied by value). |
| `procedural_failure_primary/secondary` | `Procedural failure primary/secondary` | same labels | Era 1 `…tertiary` exists but era 2 has none; tertiary not mapped (era-1-only detail). |
| `operational_mode_primary` | `Operational Mode - Primary` | `Operational Mode - Primary` | Secondary+ levels not in canonical core. |
| `ignition_occurred` | `Did ignition occur` | `Did ignition occur?` | Question mark drift between eras. |
| `process_or_non_process` | `Non-process/ Process?` | — (absent) | Era 2 has no explicit column; comes out all-NA there. |
| `non_process_type` | `Non Process Type` | ` Non Process Type` (leading space) | Leading space in era 2 is genuine. |

Unmapped source columns (94 in era 1, 128 in era 2) are **dropped from
the canonical view, not deleted** — they remain reachable through
`hcr.ingest` for ad-hoc work.

## Derived field

| Field | Derivation | Rationale |
|---|---|---|
| `non_process` (boolean) | Era 1: `process_or_non_process == 'NON-PROCESS'`. Era 2: `non_process_type` populated. | Agreed decision: **flag, don't drop**. No explicit deliberate-release flag exists in the public data; `non_process` is the closest observable proxy. Deliberate *process* releases (e.g. planned blowdowns) cannot be reliably isolated — documented limitation. `clean.drop_deliberate_releases` exists as an opt-in filter only. |

## Era-level decisions

| Decision | Detail | Rationale |
|---|---|---|
| Header offsets | Era 1 header = row 1; era 2 = row 0 | Row 0 of era 1 is group banners (`INSTALLATION DETAILS`, …). |
| `BLANK` sentinel → NA | 43,149 cells, 85/118 era-1 columns | Literal string `BLANK` means missing; done in cleaning, raw untouched. |
| Hole `999` → NA | 163 era-1 records | Unknown-size code; 999 mm would otherwise pass a ≤1000 mm plausibility check. |
| Empty rows dropped | 16 rows, 2016 sheet | All-NA padding rows, no information. |
| Phantom columns ignored | 2017 `D`, `D.1`, `D.2` | Stray keystrokes; unmapped, so excluded by the canonical reindex. |
| Case+whitespace normalisation only | e.g. `Minor`→`MINOR`, `'NORMAL PRODUCTION  '`→`'NORMAL PRODUCTION'` | Lossless. Synonym mapping (e.g. `WELLOPS` vs `WELL OPERATION`, era-2 free-text causes) changes meaning → deferred to an explicit reviewable table (Day 3+ TODO), fed by the failing rows from `cause_category_resolvable`. |
| Severity permitted set | `{MAJOR, SIGNIFICANT, MINOR, AWAITING CLASSIFICATION}` | Observed values. Era-1's single `NON-PROCESS` severity row deliberately fails validation instead of being laundered. |
| Reporting period | 1992-10-01 → 2021-12-31 | Official start per the file's Introduction; last published row-level year. The 1992-09-26 record deliberately fails. |
| Hole plausibility bounds | (0, 1000] mm | >0 (zero-diameter hole cannot release); 1000 mm = largest genuine observed value. Judgement call. |
| Cause taxonomy = era-1 closed sets | See `schema.CAUSE_TAXONOMY` | Era 1 is coded-list clean; era 2 is free-text contaminated. Validating era 2 against era-1 sets *measures* the contamination. |

## Validation results on the real data (post-cleaning, 5,278 records)

| Rule | Failures | Pass rate | Failures explained |
|---|---|---|---|
| `hole_size_within_plausible_bounds` | 2 | 99.96% | Two 0 mm entries (one per era). |
| `severity_in_permitted_set` | 1 | 99.98% | The era-1 `NON-PROCESS` severity row. |
| `date_within_reporting_period` | 1 | 99.98% | The 1992-09-26 record predating official collection. |
| `cause_category_resolvable` | 312 | 94.09% | **310 era-2 rows (~50% of era 2)** with free-text/typo cause entries; 2 era-1 rows where description text bled into the taxonomy column. |

The cause-resolvability number is the headline: the post-2016 reporting
regime lost the coded cause taxonomy in practice. This feeds Day 3
(normalisation mapping for recoverable entries) and the Day 7 report.
