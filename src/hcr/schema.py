"""Canonical schema and year-to-source-column mapping for the HCR data.

Everything here is derived from inspection of the two real files (see
``reports/inventory.md``); no column names or category values are
invented. The full judgement-call table (source column, target column,
years affected, decision, rationale) lives in
``reports/schema_mapping.md``.

Two schema eras with zero exact column-name overlap:

* **Era 1 (1992–2015)** — ``hsr1992–2014.xlsx``, sheet ``Results``,
  header on row index 1 (row 0 is group banners), 4,656 records,
  record key ``HCRDID``.
* **Era 2 (2016–2021)** — ``hcr2016-2021.xlsx``, one sheet per year
  (``HCRs 2016 Final`` … ``HCRs 2021 Provisional``), header on row 0,
  622 records after dropping empty padding rows, record key ``URN``.

The canonical schema is deliberately a **core subset** (~20 fields
needed by the validation/profiling/analysis stages), not all 118/150
source columns. Unmapped source columns remain available via
:mod:`hcr.ingest`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical column schema: {canonical_name: dtype_string}
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS: dict[str, str] = {
    "record_id": "string",
    "event_date": "datetime64[ns]",
    "severity": "string",
    "hole_diameter_mm": "float64",
    "quantity_released_kg": "float64",
    "system_primary": "string",
    "system_secondary": "string",
    "system_tertiary": "string",
    "system_quaternary": "string",
    "equipment_primary": "string",
    "equipment_secondary": "string",
    "equipment_tertiary": "string",
    "design_failure": "string",
    "equipment_failure_primary": "string",
    "equipment_failure_secondary": "string",
    "operational_failure_primary": "string",
    "operational_failure_secondary": "string",
    "procedural_failure_primary": "string",
    "procedural_failure_secondary": "string",
    "operational_mode_primary": "string",
    "ignition_occurred": "string",
    # era 1 carries an explicit PROCESS / NON-PROCESS column; era 2 does
    # not (the boolean `non_process` is derived in clean.py from these
    # two raw inputs — the only derived field in the schema):
    "process_or_non_process": "string",
    "non_process_type": "string",
}

# ---------------------------------------------------------------------------
# Source→canonical mappings, one per era. Keys are VERBATIM source
# labels, including trailing spaces, embedded newlines, and the era-1
# 'Quarternary' spelling — do not "fix" them here; they must match the
# files exactly.
# ---------------------------------------------------------------------------

ERA1_SOURCE_TO_CANONICAL: dict[str, str] = {
    "HCRDID": "record_id",
    "Incident Date": "event_date",
    "Severity": "severity",
    "Equivalent hole diameter [mm]": "hole_diameter_mm",
    "Estimated quantity released (kg) ": "quantity_released_kg",
    "System Primary": "system_primary",
    "System Secondary": "system_secondary",
    "System Tertiary": "system_tertiary",
    "System Quarternary": "system_quaternary",
    "Equipment Primary": "equipment_primary",
    "Equipment Secondary": "equipment_secondary",
    "Equipment Tertiary": "equipment_tertiary",
    # 'Design Cause' (FAILURE RELATED TO DESIGN / NO DESIGN FAILURE) is
    # kept over the redundant yes/no 'Was there a Design Failure?'
    # because its values align with era 2's design column:
    "Design Cause": "design_failure",
    "Equipment Failure Primary": "equipment_failure_primary",
    "Equipment Failure Secondary": "equipment_failure_secondary",
    "Operational Failure Primary": "operational_failure_primary",
    "Operational failure Secondary": "operational_failure_secondary",
    "Procedural failure primary": "procedural_failure_primary",
    "Procedural failure secondary": "procedural_failure_secondary",
    "Operational Mode - Primary": "operational_mode_primary",
    "Did ignition occur": "ignition_occurred",
    "Non-process/ Process?": "process_or_non_process",
    "Non Process Type": "non_process_type",
}

ERA2_SOURCE_TO_CANONICAL: dict[str, str] = {
    "URN": "record_id",
    "Event Date": "event_date",
    "Severity classification of this release\n(classified by HSL)": "severity",
    "Equivalent hole diameter [mm]": "hole_diameter_mm",
    "Estimated quantity released (KG) (converted by HSL)": "quantity_released_kg",
    "System Primary": "system_primary",
    "System Secondary": "system_secondary",
    "System Tertiary": "system_tertiary",
    "System Quaternary": "system_quaternary",
    "Equipment Primary": "equipment_primary",
    "Equipment Secondary": "equipment_secondary",
    "Equipment Tertiary": "equipment_tertiary",
    "Design Failure related to Design?": "design_failure",
    "Equipment Failure Primary": "equipment_failure_primary",
    "Equipment Failure Secondary": "equipment_failure_secondary",
    "Operational Failure Primary": "operational_failure_primary",
    "Operational failure Secondary": "operational_failure_secondary",
    "Procedural failure primary": "procedural_failure_primary",
    "Procedural failure secondary": "procedural_failure_secondary",
    "Operational Mode - Primary": "operational_mode_primary",
    "Did ignition occur?": "ignition_occurred",
    # era 2 has no explicit PROCESS/NON-PROCESS column; only the type:
    " Non Process Type": "non_process_type",
}

ERA1_YEARS = range(1992, 2016)
ERA2_YEARS = range(2016, 2022)

#: Year-to-source-column mapping: {year: {source_label: canonical_name}}.
YEAR_TO_SOURCE_COLUMNS: dict[int, dict[str, str]] = {
    **{y: ERA1_SOURCE_TO_CANONICAL for y in ERA1_YEARS},
    **{y: ERA2_SOURCE_TO_CANONICAL for y in ERA2_YEARS},
}

# ---------------------------------------------------------------------------
# Physical source tables: where the records actually live in data/raw/.
# ---------------------------------------------------------------------------

SOURCE_TABLES: list[dict] = [
    {
        # filename contains U+2013 (en dash), verbatim as downloaded
        "file": "hsr1992–2014.xlsx",
        "sheet": "Results",
        "header_row": 1,  # row 0 is group banners
        "years": list(ERA1_YEARS),
    },
    *[
        {
            "file": "hcr2016-2021.xlsx",
            "sheet": f"HCRs {y} {'Provisional' if y == 2021 else 'Final'}",
            "header_row": 0,
            "years": [y],
        }
        for y in ERA2_YEARS
    ],
]

# ---------------------------------------------------------------------------
# Observed sentinels and permitted value sets (all measured from the
# files — see reports/inventory.md for counts).
# ---------------------------------------------------------------------------

#: Era 1 encodes missing values as this literal string (43,149 cells).
BLANK_SENTINEL = "BLANK"

#: Era 1 uses 999 as an unknown-hole-size code (163 records).
HOLE_DIAMETER_SENTINELS_MM = {999.0}

#: Severity values after case normalisation. The era-1 value
#: 'NON-PROCESS' (1 row) is deliberately excluded: it is not a severity
#: and should fail validation, not be laundered into the permitted set.
SEVERITY_PERMITTED = {"MAJOR", "SIGNIFICANT", "MINOR", "AWAITING CLASSIFICATION"}

#: Official reporting period: collection began 1 Oct 1992; the last
#: published row-level year is 2021 (provisional). One era-1 record is
#: dated 1992-09-26 and will (correctly) fail the date rule.
REPORTING_PERIOD = ("1992-10-01", "2021-12-31")

#: Plausibility bounds for equivalent hole diameter, in mm. Judgement
#: call: > 0 (a zero-diameter hole cannot release) and <= 1000 (largest
#: observed genuine value; era-1 max after removing the 999 sentinel).
HOLE_DIAMETER_PLAUSIBLE_MM = (0.0, 1000.0)

#: Cause taxonomies: the closed sets observed in era 1 (which is
#: coded-list clean). Era 2 entries are heavily free-text contaminated
#: (case variants, typos, whole sentences) and largely will NOT resolve
#: against these sets — that failure count is itself a data-quality
#: measurement, not a bug. Values compared after uppercasing and
#: whitespace collapse.
DESIGN_FAILURE_VALUES = {"FAILURE RELATED TO DESIGN", "NO DESIGN FAILURE"}
EQUIPMENT_FAILURE_PRIMARY_VALUES = {
    "CORROSION",
    "EROSION",
    "MATERIAL DEFECTS",
    "MECHANICAL",
    "NO EQUIPMENT FAILURE",
    "OTHER",
}
OPERATIONAL_FAILURE_PRIMARY_VALUES = {
    "DROPPED OBJECT/OTHER IMPACT",
    "IMPROPER",
    "INCORRECTLY FITTED",
    "LEFT OPEN",
    "NO OPERATIONAL FAILURE",
    "OPENED WHEN CONTAINING HC",
    "OTHER",
}
PROCEDURAL_FAILURE_PRIMARY_VALUES = {
    "DEFICIENT PROCEDURE",
    "NO PROCEDURAL FAILURE",
    "NON-COMPLIANCE",
    "OTHER",
}

#: Cause columns validated against the sets above.
CAUSE_TAXONOMY: dict[str, set[str]] = {
    "design_failure": DESIGN_FAILURE_VALUES,
    "equipment_failure_primary": EQUIPMENT_FAILURE_PRIMARY_VALUES,
    "operational_failure_primary": OPERATIONAL_FAILURE_PRIMARY_VALUES,
    "procedural_failure_primary": PROCEDURAL_FAILURE_PRIMARY_VALUES,
}


def source_mapping_for_year(year: int) -> dict[str, str]:
    """Return the source→canonical column mapping for ``year``.

    Raises :class:`KeyError` for a year outside 1992–2021 (a missing
    year is a data gap to document, not to paper over).
    """
    return YEAR_TO_SOURCE_COLUMNS[year]


#: Category-synonym table (Day 3): {canonical_column: {observed: target}}.
#: Keys are values AS OBSERVED AFTER case/whitespace normalisation
#: (uppercase, collapsed spaces). Only meaning-preserving consolidations
#: are included — spelling variants, typos, abbreviations, and sub-values
#: whose parent category is unambiguous. Sentence-length free text and
#: genuinely new era-2 categories with no era-1 home (e.g. the EXCURSION
#: and OVERFLOW families) are deliberately NOT mapped: they keep failing
#: cause_category_resolvable, which is the honest measurement. Every
#: entry is documented in reports/schema_mapping.md.
CATEGORY_SYNONYMS: dict[str, dict[str, str]] = {
    "design_failure": {
        "YES": "FAILURE RELATED TO DESIGN",
        "NO": "NO DESIGN FAILURE",
    },
    "equipment_failure_primary": {
        "INTERNAL/EXTERNAL CORROSION": "CORROSION",
        "INTERNAL CORROSION": "CORROSION",
        "EXTERNAL CORROSION": "CORROSION",
        "MECHANICAL FAILURE DUE TO WEAR OUT / FATIGUE": "MECHANICAL",
        "MECHANICAL FAILURE DUE TO WEAR OUT": "MECHANICAL",
        "MECHANICAL FAILURE DUE TO FATIGUE": "MECHANICAL",
        "MECHANICAL FATIGUE": "MECHANICAL",
        "EQUIPMENT FAILURE MECHANICAL": "MECHANICAL",
        "MATERIAL DEFECT": "MATERIAL DEFECTS",
    },
    "operational_failure_primary": {
        "IMPROPER MAINTENANCE": "IMPROPER",
        "IMPROPER MAINTENANCE.": "IMPROPER",
        "IMPROPER MAINTENACE": "IMPROPER",
        "IMPROPER MAINTEANNCE": "IMPROPER",
        "IMPROPER OPERATION": "IMPROPER",
        "IMPROPER TESTING": "IMPROPER",
        "IMPROPER INSPECTION": "IMPROPER",
        "IMPROPER INSPECTION / MAINTENANCE / OPERATION": "IMPROPER",
        "INCORRECTLY FITTED.": "INCORRECTLY FITTED",
        "INCORRECT FITTING": "INCORRECTLY FITTED",
        "INCORRECTETLY FITTED": "INCORRECTLY FITTED",
        "INCORRRECTLY FITTED": "INCORRECTLY FITTED",
        "INCORRECTLY FIXED": "INCORRECTLY FITTED",
        "OTHER / OTHER IMPACT": "DROPPED OBJECT/OTHER IMPACT",
        "OTHER IMPACT": "DROPPED OBJECT/OTHER IMPACT",
        "IMPACT": "DROPPED OBJECT/OTHER IMPACT",
    },
    "procedural_failure_primary": {
        "NON-COMPLIANCE WITH PROCEDURE/PERMIT TO WORK": "NON-COMPLIANCE",
        "NON-COMPLIANCE WITH PROCEDURE": "NON-COMPLIANCE",
        "NON-COMPLIANCE WITH PROCEDURE.": "NON-COMPLIANCE",
        "NON-COMPLIANCE WITH": "NON-COMPLIANCE",
        "NON COMPLIANCE WITH PROCEDURE": "NON-COMPLIANCE",
        "NON COMPLIANCE WITH": "NON-COMPLIANCE",
        "NON-COMPLIANCE WITH PERMIT-TO-WORK": "NON-COMPLIANCE",
        "NON-COMPLIANCE WITH PERMIT TO WORK": "NON-COMPLIANCE",
        "NON COMPLIANCE WITH PERMIT TO WORK": "NON-COMPLIANCE",
        "NO": "NO PROCEDURAL FAILURE",
        "NO PROCEDURAL CAUSE": "NO PROCEDURAL FAILURE",
        # observed in the procedural column; reads as a data-entry slip
        # for "no failure" — documented judgement call:
        "NO OPERATIONAL FAILURE": "NO PROCEDURAL FAILURE",
        "DEFICIENT PROCEDURES": "DEFICIENT PROCEDURE",
        "DEFICENT PROCEDURE": "DEFICIENT PROCEDURE",
    },
    "system_primary": {
        # spelling drift across the era boundary, observed both sides:
        "DRILLINGEQUIPMENT": "DRILLING EQUIPMENT",
        "DRILLINGOPS": "DRILLING OPERATIONS",
        "DRILLING OPS": "DRILLING OPERATIONS",
        "DRILING OPS": "DRILLING OPERATIONS",
    },
    "operational_mode_primary": {
        # era 1 uses both spellings of the same modes:
        "WELLOPS": "WELL OPERATION",
        "DRILLINGOPS": "DRILLING OPERATION",
        "DRILLING": "DRILLING OPERATION",
        "WELLS OPS WITH TREE": "WELL OPERATIONS WITH TREE",
        "WELL OPERATION WITH TREE": "WELL OPERATIONS WITH TREE",
        "WELL OPERATIONS WITHOT TREE": "WELL OPERATIONS WITHOUT TREE",
        "START UP": "STARTUP",
        "OPERATIONAL MODE STARTUP": "STARTUP",
        "COMISSIONING": "COMMISSIONING",
        "MAINTENANCE (PLANNED)": "PLANNED MAINTENANCE",
        "MAINTENANCE (CORRECTIVE)": "CORRECTIVE MAINTENANCE",
        "PIPELINE OPERATIONAL INCLUDING PIGGING": (
            "PIPELINE OPERATIONS INCLUDING PIGGING"
        ),
        "PIGGING/PIPELINE OPERATIONS INCLUDING PIGGING": (
            "PIPELINE OPERATIONS INCLUDING PIGGING"
        ),
    },
}
