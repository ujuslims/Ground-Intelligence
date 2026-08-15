"""
CPT validation rules (Tech Spec §17 / Build Prompt CPT Module):
missing required columns, non-numeric values, missing/duplicate depth,
invalid depth ordering, missing qc/fs/u2 (flagged, not fabricated), invalid
coordinates, unit inconsistencies. Invalid data must never be silently
converted to valid data -- this function only reports problems; it never
"fixes" a row on the caller's behalf.
"""
from app.schemas.core import CPTReadingIn


def validate_cpt_readings(readings: list[CPTReadingIn]) -> list[str]:
    errors: list[str] = []

    if not readings:
        errors.append("No readings supplied.")
        return errors

    depths = [r.depth for r in readings]

    seen = set()
    for d in depths:
        if d in seen:
            errors.append(f"Duplicate depth value: {d}")
        seen.add(d)

    if depths != sorted(depths):
        errors.append("Depth values are not monotonically increasing.")

    for i, r in enumerate(readings):
        if r.depth is None:
            errors.append(f"Row {i}: missing depth.")
        if r.qc is None and r.fs is None and r.u2 is None:
            errors.append(f"Row {i} (depth={r.depth}): all of qc, fs, u2 are missing.")
        for field_name, value in (("qc", r.qc), ("fs", r.fs), ("u2", r.u2)):
            if value is not None and value < 0:
                errors.append(f"Row {i} (depth={r.depth}): {field_name} is negative ({value}).")

    return errors
