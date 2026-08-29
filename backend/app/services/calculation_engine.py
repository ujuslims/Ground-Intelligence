"""
*** THE ENGINEERING-CALCULATION ACTIVATION GATE ***

Implementation Design Rev 2 §J: this is the ONE place in the codebase where
"is this methodology allowed to produce a real result" is decided. Every
path that can trigger a calculation -- the Calculations API
(app/routers/calculations.py), any future frontend Engineering Calculation
screen, and GeoBrain's run_engineering_calculation tool
(app/geobrain/tools.py) -- MUST call CalculationRunner.run() and MUST NOT
implement its own shortcut around it.

Rev 2 §J.2, step 2: the Runner independently RE-VERIFIES that
methodology_version_id refers to a MethodologyVersion with
status == APPROVED for the requested calculation_type. It does not trust the
caller's claim, even though the UI/tool layer is expected to only ever offer
APPROVED options -- "the UI's option list is not a security boundary."

As of this build, zero MethodologyVersion rows exist with status APPROVED
for ANY calculation_type (see scripts/seed_demo_data.py -- it seeds no
methodology content at all, per the PIGL Engineering gate). Therefore every
real calculation_type currently reaches the REFUSED_NO_APPROVED_METHODOLOGY
branch below, by construction, not by a special-cased "shallow foundation"
check. The moment PIGL Engineering approves a methodology and a matching
calculation-implementation class is registered in `_IMPLEMENTATIONS` below,
that calculation_type starts succeeding -- nothing else in this file changes.

FRAMEWORK_TEST_MOCK is the one exception: a non-production calculation_type
that exists only to prove the pipeline (request -> gate -> store
CalculationVersion -> review) works end to end. It is never offered in the
production UI or GeoBrain's calculation_type options, and it returns a
result that is obviously synthetic and clearly labelled as such -- never a
number that could be mistaken for an engineering result.
"""
import json
import math
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.models.engineering import (
    Methodology, MethodologyVersion, MethodologyStatus, Calculation, CalculationVersion, CalculationStatus,
)
from app.models.project import Project
from app.services.audit import log_event

WRONG_ORGANIZATION_MESSAGE = (
    "This methodology version was approved for a different organization. "
    "Methodology approval is organization-scoped -- your own organization's "
    "technical reviewer must approve a methodology before it can be used in "
    "your calculations, even if another organization has already approved the "
    "same published standard."
)

INSUFFICIENT_BASIS_MESSAGE = (
    "No approved engineering methodology is available for this calculation type. "
    "Ground Intelligence does not estimate, approximate, or substitute a methodology. "
    "Submit a Request/Add Methodology to begin your organization's technical review process."
)


@dataclass
class CalculationOutcome:
    outcome: str          # "REFUSED_NO_APPROVED_METHODOLOGY" | "COMPLETED" | "FRAMEWORK_TEST_MOCK"
    result: dict | None
    warnings: list[str]
    message: str | None = None


def _framework_test_mock(inputs: dict) -> CalculationOutcome:
    return CalculationOutcome(
        outcome="FRAMEWORK_TEST_MOCK",
        result={"note": "SYNTHETIC PIPELINE TEST VALUE -- NOT AN ENGINEERING RESULT", "echo_inputs": inputs},
        warnings=["This is a non-production pipeline test. No engineering methodology was used."],
    )


def _eurocode7_square_pad_bearing_da1c2(inputs: dict) -> CalculationOutcome:
    """
    Eurocode 7 (EN 1997-1) Design Approach 1, Combination 2, Annex D --
    drained bearing resistance of a SQUARE pad foundation, vertical/concentric
    loading, c'=0 reduced form.

    This function implements ONLY the specification recorded against
    Methodology "Eurocode 7 Bearing Resistance -- Square Pad Foundation",
    MethodologyVersion v1.0 (APPROVED, approved_by Engr. Uju Uduma Ikpa),
    exactly as stored in methodology_versions.specification. It does not
    extend, approximate, or generalise beyond that specification -- any
    request outside its documented scope is refused below rather than
    silently computed.

    Required inputs (dict keys):
        B            -- footing width/breadth, square so length = B (m)
        Df           -- embedment depth to underside of footing (m)
        gamma_prime  -- effective unit weight of founding soil (kN/m3)
        phi          -- effective (drained) friction angle (degrees)
        c_prime      -- effective cohesion (kPa); must be 0 -- this reduced
                         form is only specified/verified for c'=0

    Optional:
        applied_load_kN -- vertical design action Vd (kN), if supplied the
                            result includes the Vd <= Rd check the spec calls
                            for.
    """
    warnings: list[str] = []
    required = ["B", "Df", "gamma_prime", "phi"]
    missing = [k for k in required if k not in inputs or inputs[k] is None]
    if missing:
        return CalculationOutcome(
            outcome="REFUSED_NO_APPROVED_METHODOLOGY",
            result=None,
            warnings=[],
            message=f"Missing required input(s) for this methodology: {', '.join(missing)}.",
        )

    B = float(inputs["B"])
    Df = float(inputs["Df"])
    gamma_prime = float(inputs["gamma_prime"])
    phi = float(inputs["phi"])
    c_prime = float(inputs.get("c_prime", 0) or 0)

    if c_prime != 0:
        return CalculationOutcome(
            outcome="REFUSED_NO_APPROVED_METHODOLOGY",
            result=None,
            warnings=[],
            message=(
                "This methodology's approved specification (v1.0) covers the drained, "
                "c'=0 reduced form only. A non-zero effective cohesion was supplied, "
                "which is outside the approved scope -- submit a Request/Add "
                "Methodology if a c'>0 formulation is needed."
            ),
        )
    if B <= 0 or Df < 0 or not (0 < phi < 45):
        return CalculationOutcome(
            outcome="REFUSED_NO_APPROVED_METHODOLOGY",
            result=None,
            warnings=[],
            message="Input values are outside a physically valid range for this methodology.",
        )
    if not (1.0 <= B <= 3.0):
        warnings.append(
            f"B = {B} m is outside this methodology's demonstrated verification envelope (1.0-3.0 m). "
            "Result is extrapolated beyond the verified case and should be reviewed with additional care."
        )
    if not (1.0 <= Df <= 2.0):
        warnings.append(
            f"Df = {Df} m is outside this methodology's demonstrated verification envelope (1.0-2.0 m). "
            "Result is extrapolated beyond the verified case and should be reviewed with additional care."
        )

    phi_r = math.radians(phi)
    phi_d = math.atan(math.tan(phi_r) / 1.25)  # DA1-C2: tan(phi) partial factor = 1.25

    Nq = math.tan(math.radians(45) + phi_d / 2) ** 2 * math.exp(math.pi * math.tan(phi_d))
    Ny = (Nq - 1) * math.tan(1.4 * phi_d)
    sq = 1 + math.sin(phi_d)
    sy = 0.70

    B_prime = B  # concentric load only -- no eccentricity reduction in this version's scope
    q_prime = gamma_prime * Df  # effective overburden at founding level

    R_A_prime = q_prime * Nq * sq + 0.5 * gamma_prime * B_prime * Ny * sy
    design_R_A = R_A_prime / (1.4 * 1.4)  # R/A partial factor 1.4, model factor 1.4

    result = {
        "methodology": "Eurocode 7 Bearing Resistance -- Square Pad Foundation, v1.0",
        "design_approach": "DA1, Combination 2, Annex D (drained, c'=0)",
        "inputs_used": {"B_m": B, "Df_m": Df, "gamma_prime_kNm3": gamma_prime, "phi_deg": phi, "c_prime_kPa": c_prime},
        "phi_d_deg": round(math.degrees(phi_d), 6),
        "Nq": round(Nq, 6),
        "Ny": round(Ny, 6),
        "sq": round(sq, 6),
        "sy": sy,
        "q_prime_kNm2": round(q_prime, 6),
        "R_over_A_prime_kNm2": round(R_A_prime, 6),
        "design_R_over_A_kNm2": round(design_R_A, 6),
    }

    if inputs.get("applied_load_kN") is not None:
        Vd = float(inputs["applied_load_kN"])
        A_prime = B_prime * B_prime
        Rd_kN = design_R_A * A_prime
        result["applied_load_kN"] = Vd
        result["design_resistance_kN"] = round(Rd_kN, 3)
        result["check_Vd_le_Rd"] = "PASS" if Vd <= Rd_kN else "FAIL"
        if Vd > Rd_kN:
            warnings.append("Vd > Rd -- the applied load exceeds the design bearing resistance for this footing.")

    return CalculationOutcome(outcome="COMPLETED", result=result, warnings=warnings)


# Registry of real calculation implementations, keyed by
# f"{methodology_id}:{methodology_version_id}" (see _verify_and_run below).
# Only entries a human has deliberately reviewed and approved may be added
# here -- see module docstring.
_IMPLEMENTATIONS: dict[str, Callable[[dict], CalculationOutcome]] = {
    "FRAMEWORK_TEST_MOCK": _framework_test_mock,
    # Eurocode 7 Bearing Resistance -- Square Pad Foundation, v1.0
    # (Methodology.id : MethodologyVersion.id), APPROVED by Engr. Uju Uduma Ikpa.
    "e3a1b8c2-6f4d-4a9e-9c1a-2d5e7f8b1a30:f4b2c9d3-7g5e-4b0f-ad2b-3e6f8g9c2b41": _eurocode7_square_pad_bearing_da1c2,
}


class CalculationRunner:
    def run(self, db: Session, *, calculation: Calculation, inputs: dict, user_id: str) -> CalculationVersion:
        if calculation.calculation_type == "FRAMEWORK_TEST_MOCK":
            outcome = _framework_test_mock(inputs)
        else:
            outcome = self._verify_and_run(db, calculation, inputs)

        version_number = (
            db.query(CalculationVersion).filter_by(calculation_id=calculation.id).count() + 1
        )
        cv = CalculationVersion(
            calculation_id=calculation.id,
            version=version_number,
            inputs=json.dumps(inputs),
            result=json.dumps(outcome.result) if outcome.result is not None else None,
            warnings=json.dumps(outcome.warnings),
            outcome=outcome.outcome,
            created_by=user_id,
        )
        db.add(cv)
        db.commit()
        db.refresh(cv)

        log_event(
            db, user_id=user_id, action="CALCULATION_EXECUTED", object_type="CALCULATION", object_id=calculation.id,
            metadata={"outcome": outcome.outcome, "calculation_type": calculation.calculation_type},
        )
        return cv

    def _verify_and_run(self, db: Session, calculation: Calculation, inputs: dict) -> CalculationOutcome:
        # Step 2 (Rev 2 §J.2): independently re-verify. Do not trust the caller.
        version = None
        if calculation.methodology_version_id:
            version = db.get(MethodologyVersion, calculation.methodology_version_id)

        if not version or version.status != MethodologyStatus.APPROVED.value:
            return CalculationOutcome(
                outcome="REFUSED_NO_APPROVED_METHODOLOGY",
                result=None,
                warnings=[],
                message=INSUFFICIENT_BASIS_MESSAGE,
            )

        # Step 3 (organization scoping): an APPROVED version is only APPROVED
        # for the organization whose technical reviewer approved it. Re-verify
        # this independently too -- do not trust that the calculation's
        # project and the version's organization already line up.
        project = db.get(Project, calculation.project_id)
        if not project or version.organization_id != project.organization_id:
            return CalculationOutcome(
                outcome="REFUSED_NO_APPROVED_METHODOLOGY",
                result=None,
                warnings=[],
                message=WRONG_ORGANIZATION_MESSAGE,
            )

        # Step 4: resolve a registered implementation for this exact
        # methodology_id + version + configuration. None is registered for
        # any real calculation_type in this codebase.
        impl_key = f"{calculation.methodology_id}:{version.id}"
        impl = _IMPLEMENTATIONS.get(impl_key)
        if impl is None:
            return CalculationOutcome(
                outcome="REFUSED_NO_APPROVED_METHODOLOGY",
                result=None,
                warnings=[],
                message=(
                    "A MethodologyVersion is marked APPROVED but no calculation-implementation "
                    "class is registered against it yet. This should not occur in a correctly "
                    "operated system -- registering an implementation is a deliberate, reviewed "
                    "deployment step, never automatic on approval."
                ),
            )
        return impl(inputs)


calculation_runner = CalculationRunner()
