"""
Synthetic demonstration data (Build Prompt "DEMONSTRATION DATA" requirement).

DEMONSTRATION DATA — NOT REAL PIGL PROJECT DATA.

Every record created by this script carries an unambiguous label so it can
never be mistaken for actual PIGL engineering data. It deliberately creates
NO Methodology / MethodologyVersion content -- see
app/services/calculation_engine.py for why that must stay empty until PIGL
Engineering approves a real methodology.

Run with: python -m scripts.seed_demo_data   (after seed_rbac.py)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

from app.core.database import SessionLocal, Base, engine
from app import models  # noqa: F401
from app.core.security import hash_password
from app.models.identity import User, Role, ProjectMembership
from app.models.project import Organization, Project
from app.models.investigation import Investigation, InvestigationLocation
from app.models.geotech import Borehole, BoreholeStratum, SPT, CPT, CPTReading, Sample, LaboratoryResult, GroundwaterObservation
from app.models.geophysics import VES, VESReading, VESLayer

DEMO_LABEL = "DEMONSTRATION DATA — NOT REAL PIGL PROJECT DATA"


def seed():
    Base.metadata.create_all(engine)
    from scripts.seed_rbac import seed as seed_rbac
    seed_rbac()

    db = SessionLocal()
    try:
        if db.query(Organization).filter_by(name="PIGL Demonstration Organization").first():
            print("Demo data already present -- skipping.")
            return

        org = Organization(name="PIGL Demonstration Organization")
        db.add(org)
        db.flush()

        user = db.query(User).filter_by(email="demo.engineer@pigl.example").first()
        if not user:
            user = User(email="demo.engineer@pigl.example", full_name="Demo Engineer",
                        password_hash=hash_password("DemoPass123!"), organization_id=org.id)
            db.add(user)
            db.flush()

        project = Project(
            organization_id=org.id, name="Demo Site Investigation — " + DEMO_LABEL,
            project_code="DEMO-001", description=DEMO_LABEL, created_by=user.id,
        )
        db.add(project)
        db.flush()

        engineer_role = db.query(Role).filter_by(name="ENGINEER").first()
        db.add(ProjectMembership(project_id=project.id, user_id=user.id, role_id=engineer_role.id))

        investigation = Investigation(
            project_id=project.id, name="Phase 1 Geotechnical Investigation (" + DEMO_LABEL + ")",
            investigation_type="GEOTECHNICAL", created_by=user.id,
        )
        db.add(investigation)
        db.flush()

        # Borehole
        bh_loc = InvestigationLocation(
            project_id=project.id, investigation_id=investigation.id, location_code="BH-01",
            location_type="BOREHOLE", latitude=6.5244, longitude=3.3792, elevation=12.4,
            source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id,
        )
        db.add(bh_loc)
        db.flush()
        bh = Borehole(location_id=bh_loc.id, borehole_id_label="BH-01", drilling_date=date(2026, 6, 10),
                      drilling_method="Rotary Wash Boring", final_depth=15.0, remarks=DEMO_LABEL,
                      source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id)
        db.add(bh)
        db.flush()
        db.add_all([
            BoreholeStratum(borehole_id=bh.id, depth_from=0.0, depth_to=2.0,
                             observed_description="Brown silty SAND, loose, moist",
                             interpreted_unit="Fill / Made Ground", source="NATIVE_GROUND_INTELLIGENCE",
                             status="INTERPRETED", created_by=user.id),
            BoreholeStratum(borehole_id=bh.id, depth_from=2.0, depth_to=8.0,
                             observed_description="Grey sandy CLAY, firm to stiff",
                             interpreted_unit="Residual Clay", source="NATIVE_GROUND_INTELLIGENCE",
                             status="INTERPRETED", created_by=user.id),
            BoreholeStratum(borehole_id=bh.id, depth_from=8.0, depth_to=15.0,
                             observed_description="Completely weathered SANDSTONE",
                             interpreted_unit="Weathered Bedrock", source="NATIVE_GROUND_INTELLIGENCE",
                             status="INTERPRETED", created_by=user.id),
        ])
        for depth, n in [(2.0, 8), (4.0, 14), (6.0, 18), (8.0, 24), (10.0, 32)]:
            db.add(SPT(borehole_id=bh.id, depth=depth, n_value=n, source="NATIVE_GROUND_INTELLIGENCE",
                       status="RAW", created_by=user.id))

        db.add(GroundwaterObservation(location_id=bh_loc.id, observation_date=date(2026, 6, 10),
                                       depth_to_water=3.2, measurement_method="Standpipe",
                                       source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id))

        # Sample + lab results (Path B -- imported)
        sample = Sample(borehole_id=bh.id, sample_id_label="BH-01-S1", depth_from=2.0, depth_to=2.45,
                         sample_type="Disturbed", source="PIGL_INTERNAL_EXTERNAL_PROCESSING",
                         status="IMPORTED", created_by=user.id)
        db.add(sample)
        db.flush()
        for rtype, val, unit in [
            ("MOISTURE_CONTENT", 22.4, "%"), ("LIQUID_LIMIT", 45.0, "%"),
            ("PLASTIC_LIMIT", 21.0, "%"), ("PLASTICITY_INDEX", 24.0, "%"),
        ]:
            db.add(LaboratoryResult(sample_id=sample.id, result_type=rtype, value=val, unit=unit,
                                     source="PIGL_INTERNAL_EXTERNAL_PROCESSING", status="IMPORTED", created_by=user.id))

        # CPT
        cpt_loc = InvestigationLocation(
            project_id=project.id, investigation_id=investigation.id, location_code="CPT-01",
            location_type="CPT", latitude=6.5250, longitude=3.3800, elevation=12.1,
            source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id,
        )
        db.add(cpt_loc)
        db.flush()
        cpt = CPT(location_id=cpt_loc.id, cpt_id_label="CPT-01", cone_type="10 cm2 subtraction cone",
                  test_date=date(2026, 6, 11), source="NATIVE_GROUND_INTELLIGENCE", status="VALIDATED",
                  created_by=user.id)
        db.add(cpt)
        db.flush()
        for i in range(0, 20):
            depth = i * 0.5
            db.add(CPTReading(cpt_id=cpt.id, depth=depth, qc=1.0 + depth * 0.8, fs=0.02 + depth * 0.01, u2=0.01 + depth * 0.02))

        # VES
        ves_loc = InvestigationLocation(
            project_id=project.id, investigation_id=investigation.id, location_code="VES-01",
            location_type="VES", latitude=6.5260, longitude=3.3810, elevation=13.0,
            source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id,
        )
        db.add(ves_loc)
        db.flush()
        ves = VES(location_id=ves_loc.id, ves_id_label="VES-01", array_type="Schlumberger",
                  survey_date=date(2026, 6, 12), interpretation_status="INTERPRETED",
                  source="NATIVE_GROUND_INTELLIGENCE", status="RAW", created_by=user.id)
        db.add(ves)
        db.flush()
        for spacing, rho in [(1, 120), (5, 95), (10, 60), (20, 40), (50, 25)]:
            db.add(VESReading(ves_id=ves.id, electrode_spacing=spacing, apparent_resistivity=rho))
        for layer_no, resistivity, thickness, interp in [
            (1, 120, 1.5, "Dry topsoil / fill"),
            (2, 60, 4.0, "Weathered laterite"),
            (3, 25, None, "Saturated sand/aquifer (interpreted)"),
        ]:
            db.add(VESLayer(ves_id=ves.id, layer_number=layer_no, resistivity=resistivity, thickness=thickness,
                             interpretation=interp, source="NATIVE_GROUND_INTELLIGENCE", status="INTERPRETED",
                             created_by=user.id))

        db.commit()
        print(f"Seeded demo project '{project.name}' (login: demo.engineer@pigl.example / DemoPass123!)")
        print(DEMO_LABEL)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
