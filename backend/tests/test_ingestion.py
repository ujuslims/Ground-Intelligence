from app.services.ingestion import inspect_cpt_csv, inspect_lab_csv, parse_cpt_csv, parse_lab_csv

CPT_CSV = b"""Depth (m),Cone Resistance qc (MPa),Sleeve Friction fs (MPa),Pore Pressure u2 (MPa)
0.0,1.0,0.02,0.01
0.5,1.4,0.03,0.02
1.0,1.8,0.04,0.03
"""

CPT_CSV_BAD = b"""Depth (m),Cone Resistance qc (MPa),Sleeve Friction fs (MPa),Pore Pressure u2 (MPa)
0.0,1.0,0.02,0.01
0.5,not_a_number,0.03,0.02
"""

LAB_CSV = b"""Sample,Test,Value,Units
BH-01-S1,MOISTURE_CONTENT,22.4,%
BH-01-S1,LIQUID_LIMIT,45.0,%
"""


def test_inspect_cpt_csv_proposes_mapping():
    result = inspect_cpt_csv(CPT_CSV)
    assert result.row_count == 3
    assert result.proposed_mapping["depth"] == "Depth (m)"
    assert result.proposed_mapping["qc"] == "Cone Resistance qc (MPa)"
    assert result.proposed_mapping["fs"] == "Sleeve Friction fs (MPa)"
    assert result.proposed_mapping["u2"] == "Pore Pressure u2 (MPa)"


def test_parse_cpt_csv_with_confirmed_mapping():
    mapping = inspect_cpt_csv(CPT_CSV).proposed_mapping
    parsed = parse_cpt_csv(CPT_CSV, mapping)
    assert parsed.errors == []
    assert len(parsed.rows) == 3
    assert parsed.rows[0]["qc"] == 1.0


def test_parse_cpt_csv_reports_non_numeric_without_importing():
    mapping = inspect_cpt_csv(CPT_CSV_BAD).proposed_mapping
    parsed = parse_cpt_csv(CPT_CSV_BAD, mapping)
    assert len(parsed.errors) == 1
    assert "non-numeric" in parsed.errors[0]
    # The good row is still parsed on its own -- the row-level error does not
    # silently convert the bad row into anything importable, but it doesn't
    # need to fail the whole file either.
    assert len(parsed.rows) == 1


def test_parse_cpt_csv_missing_depth_mapping_refuses():
    parsed = parse_cpt_csv(CPT_CSV, {"depth": None, "qc": None, "fs": None, "u2": None})
    assert parsed.rows == []
    assert "depth" in parsed.errors[0]


def test_inspect_and_parse_lab_csv():
    result = inspect_lab_csv(LAB_CSV)
    assert result.proposed_mapping["sample_id_label"] == "Sample"
    assert result.proposed_mapping["result_type"] == "Test"

    parsed = parse_lab_csv(LAB_CSV, result.proposed_mapping)
    assert parsed.errors == []
    assert len(parsed.rows) == 2
    assert parsed.rows[0]["result_type"] == "MOISTURE_CONTENT"
    assert parsed.rows[0]["value"] == 22.4
