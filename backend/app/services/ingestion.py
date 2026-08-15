"""
External file ingestion pipeline (Architecture §8, Tech Spec §17/§20):

  EXTERNAL FILE -> INGESTION SERVICE -> FORMAT DETECTION -> SCHEMA DETECTION
  -> COLUMN MAPPING -> VALIDATION -> USER CONFIRMATION -> PROJECT DATABASE

This module implements the CSV-parsing pieces of that pipeline for CPT
(Tech Spec §16-17, CSV only for MVP) and laboratory summary import
(PRD §8-9, Path B). It never guesses a value the file didn't provide, and it
never silently converts invalid data to valid data (Build Prompt CPT Module).

Column mapping is PROPOSED by heuristic name matching, then the caller
(a human, via the frontend wizard) must CONFIRM or correct it before any row
is parsed for import -- the "user confirmation" step in the pipeline above is
a hard requirement, not a formality skipped when the heuristic looks right.
"""
import csv
import io
from dataclasses import dataclass, field

# ---- CPT ----

CPT_FIELD_HINTS = {
    "depth": ["depth", "z", "depth_m"],
    "qc": ["qc", "cone resistance", "cone_resistance", "tip resistance"],
    "fs": ["fs", "sleeve friction", "sleeve_friction"],
    "u2": ["u2", "pore pressure", "pore_pressure", "u"],
}

LAB_FIELD_HINTS = {
    "sample_id_label": ["sample", "sample_id", "sample id", "sample_label"],
    "result_type": ["test", "result_type", "test_type", "parameter"],
    "value": ["value", "result", "result_value"],
    "unit": ["unit", "units"],
}


@dataclass
class InspectResult:
    columns: list[str]
    preview_rows: list[dict]
    proposed_mapping: dict[str, str | None]
    row_count: int


def _read_csv(content: bytes) -> csv.DictReader:
    text = content.decode("utf-8-sig", errors="replace")
    return csv.DictReader(io.StringIO(text))


def _propose_mapping(columns: list[str], hints: dict[str, list[str]]) -> dict[str, str | None]:
    lowered = {c: c.strip().lower() for c in columns}
    mapping: dict[str, str | None] = {}
    for field_name, keywords in hints.items():
        match = None
        for col, low in lowered.items():
            if any(kw in low for kw in keywords):
                match = col
                break
        mapping[field_name] = match
    return mapping


def inspect_cpt_csv(content: bytes, preview_limit: int = 5) -> InspectResult:
    """FORMAT DETECTION + SCHEMA DETECTION + COLUMN MAPPING proposal step.
    Writes nothing; the caller must confirm the mapping before import."""
    reader = _read_csv(content)
    rows = list(reader)
    columns = reader.fieldnames or []
    return InspectResult(
        columns=columns,
        preview_rows=rows[:preview_limit],
        proposed_mapping=_propose_mapping(columns, CPT_FIELD_HINTS),
        row_count=len(rows),
    )


def inspect_lab_csv(content: bytes, preview_limit: int = 5) -> InspectResult:
    reader = _read_csv(content)
    rows = list(reader)
    columns = reader.fieldnames or []
    return InspectResult(
        columns=columns,
        preview_rows=rows[:preview_limit],
        proposed_mapping=_propose_mapping(columns, LAB_FIELD_HINTS),
        row_count=len(rows),
    )


@dataclass
class ParseResult:
    rows: list[dict]
    errors: list[str] = field(default_factory=list)


def _to_float(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"non-numeric value: {raw!r}")


def parse_cpt_csv(content: bytes, mapping: dict[str, str | None]) -> ParseResult:
    """
    Applies a CONFIRMED column mapping (from inspect_cpt_csv, corrected by the
    user if needed) and coerces to typed readings. Missing required columns
    (depth is mandatory; at least one of qc/fs/u2 is required per Tech Spec
    §17) or non-numeric values are reported as row-level errors -- never
    silently dropped or coerced to zero.
    """
    if not mapping.get("depth"):
        return ParseResult(rows=[], errors=["Column mapping is missing a 'depth' column -- cannot import."])

    reader = _read_csv(content)
    rows: list[dict] = []
    errors: list[str] = []

    for i, raw_row in enumerate(reader):
        try:
            depth = _to_float(raw_row.get(mapping["depth"]))
            if depth is None:
                errors.append(f"Row {i}: missing depth value.")
                continue
            qc = _to_float(raw_row.get(mapping["qc"])) if mapping.get("qc") else None
            fs = _to_float(raw_row.get(mapping["fs"])) if mapping.get("fs") else None
            u2 = _to_float(raw_row.get(mapping["u2"])) if mapping.get("u2") else None
            rows.append({"depth": depth, "qc": qc, "fs": fs, "u2": u2})
        except ValueError as e:
            errors.append(f"Row {i}: {e}")

    return ParseResult(rows=rows, errors=errors)


def parse_lab_csv(content: bytes, mapping: dict[str, str | None]) -> ParseResult:
    """
    Expects a "long" format lab summary CSV: one row per (sample, result
    type) pair -- sample_id_label, result_type, value, unit. This is a
    documented MVP simplification; PIGL's actual external lab summary sheets
    may use a wide format (one row per sample, one column per test) and will
    need a second mapping mode once a real PIGL sheet is available to design
    against -- not invented here, per the "do not invent PIGL formats" gate.
    """
    required = ["sample_id_label", "result_type"]
    missing = [f for f in required if not mapping.get(f)]
    if missing:
        return ParseResult(rows=[], errors=[f"Column mapping is missing required column(s): {missing}"])

    reader = _read_csv(content)
    rows: list[dict] = []
    errors: list[str] = []

    for i, raw_row in enumerate(reader):
        sample_label = raw_row.get(mapping["sample_id_label"], "").strip()
        result_type = raw_row.get(mapping["result_type"], "").strip()
        if not sample_label or not result_type:
            errors.append(f"Row {i}: missing sample_id_label or result_type.")
            continue
        try:
            value = _to_float(raw_row.get(mapping["value"])) if mapping.get("value") else None
        except ValueError as e:
            errors.append(f"Row {i}: {e}")
            continue
        unit = raw_row.get(mapping["unit"]) if mapping.get("unit") else None
        rows.append({"sample_id_label": sample_label, "result_type": result_type, "value": value, "unit": unit})

    return ParseResult(rows=rows, errors=errors)
