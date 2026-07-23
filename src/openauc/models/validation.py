"""Structural (data-model) validation for a canonical experiment.

This validates representational consistency only — identifier uniqueness,
agreement between scan metadata and observations, physically-meaningful radius
values, and well-defined optical-system/signal-unit combinations. It is **not**
scientific quality control: it does not detect convection, aggregation or
equilibrium, estimate a meniscus, or judge whether a run is suitable for
sedimentation analysis. Field-level invariants (finiteness, non-negative time
and wavelength, valid masks) are enforced earlier, at construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from openauc.exceptions import StructuralValidationError
from openauc.models.enums import (
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from openauc.models.experiment import AUCExperiment

__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "validate_experiment_structure",
]

# Well-defined optical-system → acceptable signal-unit combinations. Systems and
# units absent from this map (or marked UNKNOWN/OTHER) are not judged.
_COMPATIBLE_UNITS: dict[OpticalSystem, frozenset[Unit]] = {
    OpticalSystem.ABSORBANCE: frozenset({Unit.ABSORBANCE_UNIT}),
    OpticalSystem.INTERFERENCE: frozenset({Unit.FRINGE}),
    OpticalSystem.FLUORESCENCE: frozenset({Unit.INSTRUMENT_UNIT, Unit.CALIBRATED_UNIT}),
    OpticalSystem.INTENSITY: frozenset({Unit.INSTRUMENT_UNIT, Unit.CALIBRATED_UNIT}),
}


@dataclass(frozen=True)
class ValidationIssue:
    """A single structural-validation finding."""

    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    location: str | None = None

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.severity.value.upper()} {self.code}{where}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    """The result of structural validation: an ordered list of issues."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """True when there are no ERROR-severity issues."""
        return not any(
            issue.severity is ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.WARNING)

    def raise_if_invalid(self) -> None:
        """Raise :class:`StructuralValidationError` if any errors are present."""
        if not self.is_valid:
            raise StructuralValidationError(str(self))

    def __str__(self) -> str:
        if not self.issues:
            return "structural validation: OK (no issues)"
        header = (
            f"structural validation: {'OK' if self.is_valid else 'FAILED'} "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        return "\n".join([header, *(f"  - {issue}" for issue in self.issues)])


def _optical_system_conflicts(system: OpticalSystem, signal_unit: Unit) -> bool:
    """True only for a well-defined optical-system/signal-unit incompatibility."""
    if signal_unit in (Unit.UNKNOWN, Unit.OTHER):
        return False
    allowed = _COMPATIBLE_UNITS.get(system)
    if allowed is None:  # UNKNOWN system, or no defined rule
        return False
    return signal_unit not in allowed


def validate_experiment_structure(
    experiment: AUCExperiment,
) -> ValidationReport:
    """Validate structural consistency and return a :class:`ValidationReport`."""
    issues: list[ValidationIssue] = []

    scan_ids = [scan.scan_id for scan in experiment.scans]
    _check_id_uniqueness(scan_ids, "scan", issues)
    _check_id_uniqueness(
        [sample.sample_id for sample in experiment.samples], "sample", issues
    )

    observations = experiment.observations
    if not experiment.scans:
        issues.append(
            ValidationIssue(
                code="no_scans",
                message="experiment contains no scans",
            )
        )
    if observations.n_scans != len(experiment.scans):
        issues.append(
            ValidationIssue(
                code="scan_count_mismatch",
                message=(
                    f"observations describe {observations.n_scans} scan(s) but "
                    f"{len(experiment.scans)} scan metadata record(s) are present"
                ),
            )
        )
    elif tuple(scan_ids) != observations.scan_ids:
        issues.append(
            ValidationIssue(
                code="scan_id_mismatch",
                message=(
                    "scan metadata identifiers do not match, or are not in the "
                    "same order as, the observation scan identifiers"
                ),
            )
        )

    _check_radius_values(observations, issues)
    _check_optical_compatibility(experiment, issues)
    _check_empty_scans(experiment, issues)

    return ValidationReport(issues=tuple(issues))


def _check_id_uniqueness(
    ids: list[str], kind: str, issues: list[ValidationIssue]
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for identifier in ids:
        if identifier in seen:
            duplicates.add(identifier)
        seen.add(identifier)
    for duplicate in sorted(duplicates):
        issues.append(
            ValidationIssue(
                code=f"duplicate_{kind}_id",
                message=f"duplicate {kind} identifier: {duplicate!r}",
                location=duplicate,
            )
        )


def _check_radius_values(observations: object, issues: list[ValidationIssue]) -> None:
    from openauc.models.observations import Observations

    assert isinstance(observations, Observations)
    values = observations.valid_radius_values()
    if values.size and bool((values <= 0).any()):
        issues.append(
            ValidationIssue(
                code="non_physical_radius",
                message="radius values must be positive; found values <= 0",
            )
        )


def _check_optical_compatibility(
    experiment: AUCExperiment, issues: list[ValidationIssue]
) -> None:
    signal_unit = experiment.observations.signal_unit
    for scan in experiment.scans:
        if _optical_system_conflicts(scan.optical_system, signal_unit):
            issues.append(
                ValidationIssue(
                    code="optical_signal_unit_conflict",
                    message=(
                        f"optical system {scan.optical_system.value!r} is "
                        f"incompatible with signal unit {signal_unit.value!r}"
                    ),
                    location=scan.scan_id,
                )
            )


def _check_empty_scans(
    experiment: AUCExperiment, issues: list[ValidationIssue]
) -> None:
    observations = experiment.observations
    if observations.mode is not RadiusAxisMode.PER_SCAN:
        return
    if observations.n_scans != len(experiment.scans):
        return
    for scan, count in zip(
        experiment.scans, observations.points_per_scan(), strict=True
    ):
        if count == 0:
            issues.append(
                ValidationIssue(
                    code="empty_scan",
                    message="scan has no observations",
                    severity=ValidationSeverity.WARNING,
                    location=scan.scan_id,
                )
            )
