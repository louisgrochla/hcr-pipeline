"""hcr — cleaning and quality-profiling pipeline for the UK offshore
Hydrocarbon Release Database (HSE offshore hydrocarbon release statistics).

Modules
-------
ingest    : read raw spreadsheets from data/raw/, no cleaning
schema    : canonical column schema + year-to-source-column mapping
clean     : normalisation, deduplication, type coercion
validate  : validation rules, each returning the failing rows
profile   : data-quality profiling (missingness, drift, distributions)
"""

__all__ = ["ingest", "schema", "clean", "validate", "profile"]
