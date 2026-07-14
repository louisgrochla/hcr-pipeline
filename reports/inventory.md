# Raw data inventory — Day 1

Status of `data/raw/` as received. Facts below are measured from the files
with `hcr.ingest` plus manual inspection; nothing is assumed from
filenames or link labels (which, as documented below, disagree with the
contents).

## Files received

| File | Size | Format | Sheets | Source |
|---|---|---|---|---|
| `hsr1992–2014.xlsx` (en-dash in filename, as downloaded) | 6.5 MB | xlsx | `Intoduction` (sic), `Pivot`, `Results` | HSE offshore statistics → National Archives hosted. <!-- TODO: exact URL + retrieval date from uploader --> |
| `hcr2016-2021.xlsx` | 1.1 MB | xlsx | `HCRs 2016 Final` … `HCRs 2020 Final`, `HCRs 2021 Provisional`, `Summary Figures` | HSE offshore statistics page. <!-- TODO: exact URL + retrieval date from uploader --> |

Both parse cleanly with openpyxl. No `.xls`/`.csv` present, so no extra
dependencies needed.

## Sheet-level inventory (`hcr.ingest.inventory()`)

| file | sheet | n_rows* | n_columns* | status |
|---|---|---|---|---|
| hcr2016-2021.xlsx | HCRs 2016 Final | 116 | 150 | ok |
| hcr2016-2021.xlsx | HCRs 2017 Final | 108 | 153 | ok |
| hcr2016-2021.xlsx | HCRs 2018 Final | 101 | 150 | ok |
| hcr2016-2021.xlsx | HCRs 2019 Final | 128 | 150 | ok |
| hcr2016-2021.xlsx | HCRs 2020 Final | 94 | 150 | ok |
| hcr2016-2021.xlsx | HCRs 2021 Provisional | 91 | 150 | ok |
| hcr2016-2021.xlsx | Summary Figures | 33 | 10 | ok |
| hsr1992–2014.xlsx | Intoduction | 27 | 2 | ok |
| hsr1992–2014.xlsx | Pivot | 28 | 7 | ok |
| hsr1992–2014.xlsx | Results | 4657 | 118 | ok |

\* as read with pandas defaults (header = first row). For the old file's
`Results` sheet the true header is **row index 1** (row 0 is group
banners such as `INSTALLATION DETAILS`, `[6] EQUIVALENT HOLE DIAMETER`);
with the correct header the sheet holds **4,656 records × 118 fields**.
The new file's sheets have a single header row.

## How many schemas

**Two schema eras, zero exact column-name overlap between them.**

- **Era 1 (1992–2015)** — `hsr1992–2014.xlsx / Results`: one sheet, all
  years, 118 fields. Record key `HCRDID` (4,656/4,656 unique, no nulls).
  Two-row header. Data entered on form OIR/12, checked against RIDDOR
  OIR/9B (per the file's own Introduction sheet).
- **Era 2 (2016–2021)** — `hcr2016-2021.xlsx`: one sheet per calendar
  year, 150 fields (2017: 153 — see phantom columns below). Record key
  `URN` (622/622 unique after dropping empty rows). Long verbose labels,
  some containing embedded newlines and trailing spaces, e.g.
  `'Severity classification of this release\n(classified by HSL)'`.

Semantically corresponding fields exist across eras under different
labels (e.g. `Incident Date` ↔ `Event Date`; `Severity` ↔ the label
above; both eras: `Equivalent hole diameter [mm]`, identical label but
different position/context). Building that correspondence is the Day 2
mapping table. Verbatim column lists for both eras are preserved for the
mapping work. Spelling drift exists inside the taxonomy labels
themselves: `System Quarternary` (era 1) vs `System Quaternary` (era 2).

## Which years are present / missing

Measured from `Incident Date` / `Event Date`, not from filenames:

| Year | Rows | Notes |
|---|---|---|
| 1992 | 40 | Partial year: collection began 1 Oct 1992. One record dated 1992-09-26, i.e. before the official start. |
| 1993–2014 | 81–339 per year | Continuous. Declining trend after ~2004. |
| 2015 | 85 | **Present**, despite the filename saying 2014 and the file's own Introduction saying coverage ends 31 Dec 2014. |
| 2016–2020 | 94–128 per year (sheets marked "Final") | 2016 has 16 fully-empty padding rows (real records: 100). |
| 2021 | 91 | Sheet marked **"Provisional"**; 45 of 91 records are `Awaiting Classification` for severity. |
| 2022+ | — | Not published as row-level data; exists only in HSE's annual PDF reports. Out of scope; documented gap. |

**There is no gap year.** Era 1 runs 1992-09-26 → 2015-12-31; era 2 runs
2016-01-01 → 2021-12-19. Three public labels for the old file disagree
with the data and each other: the download-page link says "1992 – 2016",
the filename says 1992–2014, the Introduction sheet says coverage to
31 Dec 2014 — the rows say 1992–2015.

## Data-quality observations (to hunt on Day 3–5)

Catalogued now, quantified/handled later:

1. **`BLANK` string sentinel (era 1):** 43,149 cells across 85 of 118
   columns contain the literal string `BLANK` instead of an empty cell.
   Any missingness analysis that ignores this will be wrong.
2. **`999` hole-diameter sentinel (era 1):** 163 records have
   `Equivalent hole diameter [mm]` = 999, far outside the plausible
   range and clearly a missing/unknown code, not a measurement.
3. **Hole-size rounding artefact — confirmed present:** 1,002 records at
   exactly 1 mm and 224 at exactly 2 mm vs only 393 in the whole open
   interval (1, 2) mm. Inch-conversion spikes also visible (12.7, 25.4).
   To be quantified properly on Day 5.
4. **Severity category drift (era 2):** case-inconsistent values within
   the same sheets — `Minor` alongside `MINOR` (2018: 2 rows, 2020: 5
   rows); `Awaiting Classification` (2021) vs era 1's
   `AWAITING CLASSIFICATION`. Era 1 also contains one row with severity
   `NON-PROCESS`, which is not a severity.
5. **Whitespace-split categories (era 1):** e.g. `Operational Mode -
   Primary` contains `'NORMAL PRODUCTION  '` (2,494 rows, trailing
   spaces) and `'NORMAL PRODUCTION'` (44 rows) as distinct values.
6. **Phantom columns (era 2, 2017):** three stray columns (`D`, `D.1`,
   `D.2`) created by stray keystrokes in otherwise-empty cells (a
   backtick and a lone `D`).
7. **Empty padding rows (era 2, 2016):** 16 rows with no data at all
   (hence severity/date "missing" for 16 rows in naive counts).
8. **Retroactive severity classification (era 1):** severity criteria
   were introduced in 1997 and refined in 1999 (per the Introduction
   sheet), yet all 1992–1996 rows carry classifications — i.e. early
   severities were applied retrospectively under later criteria.
9. **Deliberate/planned releases:** no explicit yes/no flag found in
   either era. Candidate signals: era 1 `Non-process/ Process?`
   (PROCESS 4,085 / NON-PROCESS 571) with `Non Process Type` (DIESEL,
   LUB OIL, …); `Operational Mode - Primary` values such as
   `SHUTTING DOWN/SHUTDOWN/BLOWDOWN`. How to identify deliberate
   releases is a **judgement call requiring a decision** — TODO(Day 2/3).
10. **Voluntary reporting:** the OIR/12 return is voluntary (per the
    Introduction sheet) — an under-reporting caveat for all analysis.
11. **Filename with en-dash:** `hsr1992–2014.xlsx` contains U+2013, kept
    verbatim as downloaded; worth knowing for shell/tooling quoting.

## Keys and joins

- Era 1: `HCRDID` — unique, non-null. Usable dedup/record key.
- Era 2: `URN` — unique and non-null once empty padding rows are dropped.
- No cross-era key overlap expected (not verified yet).
