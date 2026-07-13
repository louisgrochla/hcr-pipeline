"""Ingest raw HSE hydrocarbon release files from ``data/raw/``.

This module loads files **as published** — no renaming, no type coercion,
no filtering. Cleaning belongs in :mod:`hcr.clean`.

Design constraints (from the spec):

* Different years may arrive in different formats (``.xlsx``, ``.xls``,
  ``.csv``) and with different internal structures. Nothing here assumes
  a particular layout.
* A file that cannot be parsed is **logged and skipped, never fatal**.
  The pipeline documents gaps and moves on; :func:`inventory` records the
  failure alongside the successes.

.. note::
   ``.xls`` (legacy Excel) requires the ``xlrd`` engine, which is *not* a
   declared dependency. If any real HSE year arrives as ``.xls``, the file
   will be reported as unparseable in the inventory with instructions to
   add ``xlrd``. TODO: add ``xlrd`` to dependencies if and only if the
   downloaded files require it.

.. note::
   TODO: HSE spreadsheets may carry preamble/title rows above the header
   row. Until the real files are inspected, sheets are read with the
   pandas default (first row = header) and the "detected columns" in the
   inventory must be read with that caveat. Header-row offsets, if any,
   belong in :mod:`hcr.schema` once known.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

#: Default location of raw files, relative to the repo root.
RAW_DIR = Path("data/raw")

#: File extensions the loader will attempt. Anything else is ignored
#: (and reported by :func:`inventory` as unsupported).
SUPPORTED_SUFFIXES = {".xlsx", ".xls", ".csv"}


def load_file(path: Path | str) -> dict[str | None, pd.DataFrame]:
    """Load a single raw file as-is.

    Returns a mapping of sheet name to :class:`pandas.DataFrame`. Excel
    workbooks yield one entry per sheet; CSV files yield a single entry
    keyed by ``None`` (CSV has no sheet concept).

    Raises on failure — callers that must not fail (i.e. the pipeline)
    should go through :func:`load_all` or :func:`inventory`, which catch,
    log, and skip.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported format {suffix!r} for {path.name}; "
            f"supported: {sorted(SUPPORTED_SUFFIXES)}"
        )
    if suffix == ".csv":
        return {None: pd.read_csv(path)}
    # .xlsx / .xls — read every sheet, untouched.
    return pd.read_excel(path, sheet_name=None)


def load_all(
    raw_dir: Path | str = RAW_DIR,
) -> dict[str, dict[str | None, pd.DataFrame]]:
    """Load every supported file under ``raw_dir``, skipping failures.

    Returns ``{filename: {sheet_name: DataFrame}}`` for files that parsed.
    Files that fail to parse are logged at WARNING level and omitted —
    never fatal. Use :func:`inventory` for a per-file record that
    includes the failures.
    """
    raw_dir = Path(raw_dir)
    loaded: dict[str, dict[str | None, pd.DataFrame]] = {}
    for path in sorted(raw_dir.glob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            loaded[path.name] = load_file(path)
        except Exception as exc:  # noqa: BLE001 — deliberate: document and move on
            logger.warning("Skipping unparseable file %s: %s", path.name, exc)
    return loaded


def inventory(raw_dir: Path | str = RAW_DIR) -> pd.DataFrame:
    """Report what is actually in ``raw_dir``, per file and sheet.

    One row per (file, sheet) with:

    * ``file`` — filename
    * ``format`` — file extension (lowercased, without the dot)
    * ``sheet`` — sheet name (``None`` for CSV)
    * ``n_rows`` — row count as read
    * ``n_columns`` — column count as read
    * ``columns`` — list of detected column labels, verbatim
    * ``status`` — ``"ok"``, or ``"error: ..."`` for unparseable files
      (unparseable files still get a row: gaps are part of the record)

    Unsupported extensions found in the directory are reported with
    ``status="unsupported"`` rather than silently ignored.
    """
    raw_dir = Path(raw_dir)
    records: list[dict] = []
    for path in sorted(raw_dir.glob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        fmt = path.suffix.lower().lstrip(".")
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            records.append(
                {
                    "file": path.name,
                    "format": fmt,
                    "sheet": None,
                    "n_rows": None,
                    "n_columns": None,
                    "columns": None,
                    "status": "unsupported",
                }
            )
            continue
        try:
            sheets = load_file(path)
        except Exception as exc:  # noqa: BLE001 — deliberate: document and move on
            logger.warning("Inventory: could not parse %s: %s", path.name, exc)
            records.append(
                {
                    "file": path.name,
                    "format": fmt,
                    "sheet": None,
                    "n_rows": None,
                    "n_columns": None,
                    "columns": None,
                    "status": f"error: {exc}",
                }
            )
            continue
        for sheet_name, df in sheets.items():
            records.append(
                {
                    "file": path.name,
                    "format": fmt,
                    "sheet": sheet_name,
                    "n_rows": len(df),
                    "n_columns": df.shape[1],
                    "columns": list(df.columns),
                    "status": "ok",
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["file", "format", "sheet", "n_rows", "n_columns", "columns", "status"],
    )
