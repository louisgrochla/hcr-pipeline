# Repo spec: `hcr-pipeline`
### A reproducible cleaning and quality-profiling pipeline for the UK offshore Hydrocarbon Release Database

**Purpose:** demonstrate, against a public dataset, the exact skills Imrandd's Data Analyst / Junior Data Scientist role asks for: wrangling anomaly registers and engineering exports, exploratory analysis to surface patterns and data-quality issues, and reusable well-documented Python for repeatable cleaning.

**Timebox: 7 days.** Scope creep is the enemy. No modelling until the boring part is done and documented.

---

## The data

HSE's offshore Hydrocarbon Release (HCR) data, published free as spreadsheets via HSE's offshore statistics pages. It records loss-of-containment events on UK Continental Shelf installations since October 1992, categorised by:

- severity (major / significant / minor)
- cause taxonomy (design, equipment, operation, procedural, each with sub-categories)
- equipment type
- hole size
- installation and date

This is an anomaly register for the North Sea. That is the point. Do not substitute a Kaggle dataset.

**Known messiness to hunt for and document (this is the value, not a side note):**
- Schema and category drift across three decades of reporting forms (OIR/9B, OIR12).
- Under-reporting of hole sizes between 1mm and 2mm, because reporters round down. This shows up as a visible step in the hole-size distribution.
- Partial first year (collection began October 1992, so 1992 is not a full year).
- Deliberate releases mixed in with unintentional ones.
- Free-text and inconsistent categorical entries.

---

## Deliverable structure

```
hcr-pipeline/
├── README.md                 <- written as a client deliverable, not a student readme
├── pyproject.toml
├── src/hcr/
│   ├── ingest.py             <- read raw spreadsheets, no cleaning here
│   ├── schema.py             <- canonical column names + dtypes, year-to-year mapping
│   ├── clean.py              <- normalisation, deduplication, type coercion
│   ├── validate.py           <- validation rules, each returning a pass/fail + affected rows
│   └── profile.py            <- data-quality profiling
├── tests/
│   ├── test_clean.py
│   └── test_validate.py
├── notebooks/
│   └── 01_eda.ipynb          <- exploration only; nothing load-bearing lives here
└── reports/
    └── data_quality.md       <- 2 pages, the actual output
```

**Rule:** the notebook is not the deliverable. The package is. A notebook says "student." A tested, importable package with a validation layer says "I have shipped things."

---

## Day by day

**Day 1 — Ingest.** Download every available year. Write `ingest.py` to load raw, no transformation. Record what you find: how many files, how many schemas, which years are missing. Commit the inventory.

**Day 2 — Schema.** Build the year-to-year column mapping into a canonical schema. This is the unglamorous core of the whole thing and the part that proves you can do the job. Document every judgement call in a table: source column, target column, years affected, decision, rationale.

**Day 3 — Clean.** Type coercion, category normalisation, deduplication, filtering deliberate releases. Every transformation is a named function with a docstring. No inline magic.

**Day 4 — Validate.** Validation rules as code: hole size within plausible bounds, severity in the permitted set, date within the reporting period, cause category resolvable in the taxonomy. Each rule returns the failing rows, not just a boolean. Write the tests.

**Day 5 — Profile.** Missingness by column by year. Category drift over time. The hole-size rounding artefact, plotted. Anything else that looks wrong. Quantify it.

**Day 6 — Analyse.** Cause trends by severity over time. One clear question, answered properly, with a stated method. Do not sprawl.

**Day 7 — Write.** `reports/data_quality.md`, two pages, aimed at a client, not a marker: what the data is, what's wrong with it, what you did about it, what a downstream analyst must know before trusting it. Then the README.

---

## Optional stretch (only if days 1 to 7 are genuinely finished)

Apply your NLP work to the cause categorisation: can a small fine-tuned classifier recover the cause category from the incident description, and where does it disagree with the human coder? That disagreement set is exactly the kind of label-noise finding you already surfaced on Banking77, and it is the thing that makes you memorable rather than merely competent.

But this is dessert. The pipeline is the meal.

---

## How it gets used

- Public repo, linked in the application and the email.
- One paragraph in the covering note: "I built a cleaning and quality-profiling pipeline for the HSE hydrocarbon release register, because it's the closest public analogue to the inspection records and anomaly registers in this role. The interesting finding was [X]."
- That paragraph is the entire reason they read further.
