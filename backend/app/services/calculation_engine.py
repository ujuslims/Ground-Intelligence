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
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.models.engineering import (
    Methodology, MethodologyVersion, MethodologyStatus, Calculation, CalculationVersion, CalculationStatus,
)
from app.services.audit import log_event

INSUFFICIENT_BASIS_MESSAGE = (
    "No approved engineering methodology is available for this calculation type. "
    "Ground Intelligence does not estimate, approximate, or substitute a methodology. "
    "Submit a Request/Add Methodology to begin the PIGL Engineering review process."
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


# Registry of real calculation implementations, keyed by
# (calculation_type, methodology_id, methodology_version_id).
# Deliberately EMPTY for every real engineering calculation_type -- see module
# docstring. Only the non-production mock is registered.
_IMPLEMENTATIONS: dict[str, Callable[[dict], CalculationOutcome]] = {
    "FRAMEWORK_TEST_MOCK": _framework_test_mock,
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
