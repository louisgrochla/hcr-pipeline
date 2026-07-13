# hcr-pipeline

A reproducible cleaning and quality-profiling pipeline for the UK offshore
Hydrocarbon Release Database (HSE offshore statistics).

> Status: scaffold. Ingest machinery and generic clean/validate/profile
> primitives are in place; the canonical schema (Day 2) is deliberately
> empty until the real HSE files have been inspected. See TODOs in
> `src/hcr/schema.py`.

## Purpose

<!-- TODO(Day 7): written as a client deliverable — what this pipeline is
for and what it demonstrates. -->

## The data

<!-- TODO(Day 7): what the HCR register records (loss-of-containment
events on UKCS installations since October 1992), categorisations, and
coverage of the downloaded files. -->

### Known messiness

<!-- TODO(Day 5/7): document and quantify, from the real data:
- schema and category drift across reporting forms (OIR/9B, OIR12)
- under-reporting of hole sizes between 1mm and 2mm (round-down step)
- partial first year (collection began October 1992)
- deliberate releases mixed with unintentional ones
- free-text and inconsistent categorical entries -->

## Data provenance

- **Source:** HSE offshore hydrocarbon release statistics (UK Health and
  Safety Executive, offshore statistics pages).
- **Licence:** Open Government Licence v3.0.
- **Retrieved:** <!-- TODO: fill in retrieval date and exact source URLs
  when the files are downloaded into data/raw/. -->

Raw files are not committed (`data/raw/` is gitignored); they are
re-downloadable from the source above.

## Structure

```
hcr-pipeline/
├── README.md
├── pyproject.toml
├── src/hcr/
│   ├── ingest.py             <- read raw spreadsheets, no cleaning here
│   ├── schema.py             <- canonical column names + dtypes, year-to-year mapping
│   ├── clean.py              <- normalisation, deduplication, type coercion
│   ├── validate.py           <- validation rules, each returning failing rows
│   └── profile.py            <- data-quality profiling
├── tests/
│   ├── test_clean.py
│   └── test_validate.py
├── notebooks/
│   └── 01_eda.ipynb          <- exploration only; nothing load-bearing lives here
└── reports/
    └── data_quality.md       <- 2 pages, the actual output
```

## Usage

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Drop the downloaded HSE files into `data/raw/`, then:

```python
from hcr import ingest
ingest.inventory()   # per file: format, sheets, row count, detected columns
```

## Data quality findings

<!-- TODO(Day 7): link to reports/data_quality.md and summarise the
headline findings. -->
