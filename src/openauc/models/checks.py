"""The ordered registry of validation checks.

Every check is a pure function of an :class:`~openauc.models.AUCExperiment`
returning zero or more :class:`~openauc.models.validation.ValidationIssue`
records. :data:`CHECKS` fixes their execution order, so a report's issue order
is fully determined by the experiment's content.

Two rules govern this module:

* **Nothing is inferred.** A check reports what is absent; it never supplies a
  default, guesses a unit, or decides what a value "should" be.
* **One finding per condition, not per scan.** A condition affecting many scans
  is reported once, carrying every affected scan identifier in sorted order.

The blocking sets are deliberately minimal. Metadata that a conventional AUC
workflow would merely *prefer* is reported, never required — a historical
dataset with sparse metadata stays representable, archivable and inspectable.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

from openauc.models.enums import (
    ExperimentType,
    OpticalSystem,
    RadiusAxisMode,
    Unit,
    ValidationSeverity,
    ValidationTier,
    ValueStatus,
)
from openauc.models.validation import ValidationIssue

if TYPE_CHECKING:
    from openauc.models.experiment import AUCExperiment
    from openauc.models.instrument import InstrumentMetadata
    from openauc.models.metadata import Quantity
    from openauc.models.observations import Observations
    from openauc.models.sample import SampleMetadata
    from openauc.models.scan import ScanMetadata

__all__ = ["CHECKS", "Check"]

Check = Callable[["AUCExperiment"], list[ValidationIssue]]

_ERROR = ValidationSeverity.ERROR
_WARNING = ValidationSeverity.WARNING
_INFO = ValidationSeverity.INFO

_ARCHIVAL = ValidationTier.ARCHIVAL
_STRUCTURAL = ValidationTier.STRUCTURAL
_SV = ValidationTier.SV_READINESS
_SE = ValidationTier.SE_READINESS

_READINESS = (_SV, _SE)

# Well-defined optical-system → acceptable signal-unit combinations. Systems and
# units absent from this map (or marked UNKNOWN/OTHER) are not judged.
_COMPATIBLE_UNITS: dict[OpticalSystem, frozenset[Unit]] = {
    OpticalSystem.ABSORBANCE: frozenset({Unit.ABSORBANCE_UNIT}),
    OpticalSystem.INTERFERENCE: frozenset({Unit.FRINGE}),
    OpticalSystem.FLUORESCENCE: frozenset({Unit.INSTRUMENT_UNIT, Unit.CALIBRATED_UNIT}),
    OpticalSystem.INTENSITY: frozenset({Unit.INSTRUMENT_UNIT, Unit.CALIBRATED_UNIT}),
}

#: Per-scan quantity fields whose declared units are checked for consistency.
_SCAN_QUANTITY_FIELDS = ("elapsed_time", "wavelength", "rotor_speed", "temperature")


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _is_present(quantity: Quantity | None) -> bool:
    """True only when a real numeric value is carried."""
    return quantity is not None and quantity.status is ValueStatus.PRESENT


#: Typed accessors, so quantity lookups never degrade to ``Any``.
_SCAN_QUANTITY_ACCESSORS: dict[str, Callable[[ScanMetadata], Quantity | None]] = {
    "elapsed_time": lambda scan: scan.elapsed_time,
    "wavelength": lambda scan: scan.wavelength,
    "rotor_speed": lambda scan: scan.rotor_speed,
    "temperature": lambda scan: scan.temperature,
}

_INSTRUMENT_QUANTITY_ACCESSORS: dict[
    str, Callable[[InstrumentMetadata], Quantity | None]
] = {
    "nominal_speed": lambda instrument: instrument.nominal_speed,
    "temperature": lambda instrument: instrument.temperature,
    "wavelength": lambda instrument: instrument.wavelength,
}

_SAMPLE_QUANTITY_ACCESSORS: dict[str, Callable[[SampleMetadata], Quantity | None]] = {
    "density": lambda sample: sample.density,
    "viscosity": lambda sample: sample.viscosity,
    "partial_specific_volume": lambda sample: sample.partial_specific_volume,
}


def _aggregate(
    *,
    code: str,
    message: str,
    severity: ValidationSeverity,
    tiers: tuple[ValidationTier, ...],
    subjects: Sequence[str] = (),
    blocks: tuple[ValidationTier, ...] = (),
    observed: str | None = None,
    expected: str | None = None,
    remediation: str | None = None,
    component: str | None = None,
    are_scans: bool = True,
) -> ValidationIssue:
    """Build one finding covering every affected subject.

    ``location`` is set only when exactly one subject is affected, so the
    single-subject case reads naturally while large sets stay compact.
    """
    ordered = tuple(sorted(subjects))
    return ValidationIssue(
        code=code,
        message=message,
        severity=severity,
        location=ordered[0] if len(ordered) == 1 else None,
        tiers=tiers,
        blocks=blocks,
        observed=observed,
        expected=expected,
        remediation=remediation,
        component=component,
        scan_ids=ordered if are_scans else (),
    )


def _radius_vectors(observations: Observations) -> tuple[tuple[float, ...], ...]:
    """Per-scan radius vectors with padding excluded (shared axis repeated)."""
    dataset = observations.dataset
    if observations.mode is RadiusAxisMode.SHARED:
        shared = tuple(float(v) for v in dataset["radius"].to_numpy().tolist())
        return tuple(shared for _ in range(observations.n_scans))
    radius = dataset["radius"].to_numpy()
    mask = dataset["mask"].to_numpy()
    return tuple(
        tuple(float(v) for v in np.asarray(row[keep], dtype=float).tolist())
        for row, keep in zip(radius, mask, strict=True)
    )


def _is_monotonic(values: Sequence[float]) -> bool:
    """True when ``values`` never changes direction (either order is fine)."""
    if len(values) < 2:
        return True
    pairs = list(pairwise(values))
    return all(b >= a for a, b in pairs) or all(b <= a for a, b in pairs)


def _has_duplicates(values: Sequence[float]) -> bool:
    return len(set(values)) != len(values)


def _instrument_quantity(experiment: AUCExperiment, field: str) -> Quantity | None:
    if experiment.instrument is None:
        return None
    return _INSTRUMENT_QUANTITY_ACCESSORS[field](experiment.instrument)


# --------------------------------------------------------------------------- #
# ARCHIVAL tier — unambiguous keying and correspondence
# --------------------------------------------------------------------------- #


def check_duplicate_scan_ids(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Duplicate scan identifiers make observations impossible to attribute."""
    return _duplicate_ids(
        [scan.scan_id for scan in experiment.scans],
        kind="scan",
        blocks=(_ARCHIVAL, _STRUCTURAL, _SV, _SE),
    )


def check_duplicate_sample_ids(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Duplicate sample identifiers make sample metadata ambiguous."""
    return _duplicate_ids(
        [sample.sample_id for sample in experiment.samples],
        kind="sample",
        blocks=(_ARCHIVAL, _STRUCTURAL),
    )


def _duplicate_ids(
    ids: list[str], *, kind: str, blocks: tuple[ValidationTier, ...]
) -> list[ValidationIssue]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for identifier in ids:
        if identifier in seen:
            duplicates.add(identifier)
        seen.add(identifier)
    return [
        ValidationIssue(
            code=f"duplicate_{kind}_id",
            message=f"duplicate {kind} identifier: {duplicate!r}",
            severity=_ERROR,
            location=duplicate,
            tiers=(_ARCHIVAL,),
            blocks=blocks,
            observed=f"{ids.count(duplicate)} records share {duplicate!r}",
            expected=f"every {kind} identifier occurs exactly once",
            remediation=f"give each {kind} a distinct identifier",
            component=f"{kind}_id",
            scan_ids=(duplicate,) if kind == "scan" else (),
        )
        for duplicate in sorted(duplicates)
    ]


def check_scan_observation_correspondence(
    experiment: AUCExperiment,
) -> list[ValidationIssue]:
    """Scan metadata and observations must describe the same scans, in order."""
    observations = experiment.observations
    scan_ids = tuple(scan.scan_id for scan in experiment.scans)
    blocks = (_ARCHIVAL, _STRUCTURAL, _SV, _SE)
    if observations.n_scans != len(experiment.scans):
        return [
            ValidationIssue(
                code="scan_count_mismatch",
                message=(
                    f"observations describe {observations.n_scans} scan(s) but "
                    f"{len(experiment.scans)} scan metadata record(s) are present"
                ),
                severity=_ERROR,
                tiers=(_ARCHIVAL,),
                blocks=blocks,
                observed=(
                    f"{observations.n_scans} observation scan(s), "
                    f"{len(experiment.scans)} metadata record(s)"
                ),
                expected="one scan metadata record per observation scan",
                remediation="add the missing records or remove the extra ones",
                component="scans",
            )
        ]
    if scan_ids != observations.scan_ids:
        return [
            ValidationIssue(
                code="scan_id_mismatch",
                message=(
                    "scan metadata identifiers do not match, or are not in the "
                    "same order as, the observation scan identifiers"
                ),
                severity=_ERROR,
                tiers=(_ARCHIVAL,),
                blocks=blocks,
                observed=f"metadata {list(scan_ids)} vs observations "
                f"{list(observations.scan_ids)}",
                expected="identical identifiers in identical order",
                remediation="reorder or rename so both sequences agree",
                component="scan_id",
            )
        ]
    return []


# --------------------------------------------------------------------------- #
# STRUCTURAL tier — internal consistency and inspectability
# --------------------------------------------------------------------------- #


def check_no_scans(experiment: AUCExperiment) -> list[ValidationIssue]:
    """An experiment with no scans has nothing to inspect or analyse."""
    if experiment.scans:
        return []
    return [
        ValidationIssue(
            code="no_scans",
            message="experiment contains no scans",
            severity=_ERROR,
            tiers=(_STRUCTURAL,),
            blocks=(_STRUCTURAL, _SV, _SE),
            observed="0 scans",
            expected="at least one scan",
            remediation="add the scan metadata and observations for this run",
            component="scans",
        )
    ]


def check_non_physical_radius(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Radial positions must be positive to be representable."""
    values = experiment.observations.valid_radius_values()
    if not values.size or not bool((values <= 0).any()):
        return []
    return [
        ValidationIssue(
            code="non_physical_radius",
            message="radius values must be positive; found values <= 0",
            severity=_ERROR,
            tiers=(_STRUCTURAL,),
            blocks=(_STRUCTURAL, _SV, _SE),
            observed=f"minimum radius {float(values.min()):g}",
            expected="every radius > 0",
            remediation="correct the radial axis or drop the affected points",
            component="observations.radius",
        )
    ]


def check_optical_signal_unit_conflict(
    experiment: AUCExperiment,
) -> list[ValidationIssue]:
    """A defined optical-system / signal-unit contradiction is an error.

    Unknown systems and unknown/open-ended units are never judged: the model
    does not guess.
    """
    signal_unit = experiment.observations.signal_unit
    if signal_unit in (Unit.UNKNOWN, Unit.OTHER):
        return []
    issues: list[ValidationIssue] = []
    for system in sorted(
        {scan.optical_system for scan in experiment.scans}, key=lambda s: s.value
    ):
        allowed = _COMPATIBLE_UNITS.get(system)
        if allowed is None or signal_unit in allowed:
            continue
        affected = [s.scan_id for s in experiment.scans if s.optical_system is system]
        issues.append(
            _aggregate(
                code="optical_signal_unit_conflict",
                message=(
                    f"optical system {system.value!r} is incompatible with "
                    f"signal unit {signal_unit.value!r}"
                ),
                severity=_ERROR,
                tiers=(_STRUCTURAL,),
                blocks=(_STRUCTURAL, _SV, _SE),
                subjects=affected,
                observed=f"{system.value} with {signal_unit.value}",
                expected=(
                    f"{system.value} with one of "
                    f"{sorted(u.value for u in allowed)}, or an unknown unit"
                ),
                remediation="correct the declared signal unit or optical system",
                component="observations.signal_unit",
            )
        )
    return issues


def check_empty_scans(experiment: AUCExperiment) -> list[ValidationIssue]:
    """A per-scan-axis scan carrying no observations is representable."""
    observations = experiment.observations
    if observations.mode is not RadiusAxisMode.PER_SCAN:
        return []
    if observations.n_scans != len(experiment.scans):
        return []
    empty = [
        scan.scan_id
        for scan, count in zip(
            experiment.scans, observations.points_per_scan(), strict=True
        )
        if count == 0
    ]
    if not empty:
        return []
    return [
        _aggregate(
            code="empty_scan",
            message="scan has no observations"
            if len(empty) == 1
            else f"{len(empty)} scans have no observations",
            severity=_WARNING,
            tiers=(_STRUCTURAL,),
            subjects=empty,
            observed="0 valid points",
            expected="at least one valid observation per scan",
            remediation="remove the empty scan or supply its observations",
            component="observations.mask",
        )
    ]


def check_no_observations(experiment: AUCExperiment) -> list[ValidationIssue]:
    """No valid observation anywhere leaves nothing to analyse."""
    if not experiment.scans:
        return []
    total = sum(experiment.observations.points_per_scan())
    if total:
        return []
    return [
        ValidationIssue(
            code="no_observations",
            message="the experiment carries no valid observations",
            severity=_WARNING,
            tiers=(_STRUCTURAL,),
            blocks=(_SV, _SE),
            observed="0 valid observations across all scans",
            expected="at least one valid observation",
            remediation="supply the radial signal data for at least one scan",
            component="observations",
        )
    ]


def check_radius_monotonicity(experiment: AUCExperiment) -> list[ValidationIssue]:
    """A radius vector that changes direction is anomalous but representable.

    Descending order is **not** flagged: inward scans are legitimate and order
    is preserved deliberately.
    """
    return _radius_anomaly(
        experiment,
        predicate=lambda values: not _is_monotonic(values),
        code="radius_not_monotonic",
        subject="is neither ascending nor descending throughout",
        expected="radius values ordered consistently within a scan",
        remediation="verify the source ordering; openauc never reorders data",
    )


def check_duplicate_radius(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Repeated radial positions within one scan are ambiguous but storable."""
    return _radius_anomaly(
        experiment,
        predicate=_has_duplicates,
        code="duplicate_radius_within_scan",
        subject="repeats at least one radial position",
        expected="distinct radial positions within a scan",
        remediation="deduplicate the affected radial positions at source",
    )


def _radius_anomaly(
    experiment: AUCExperiment,
    *,
    predicate: Callable[[tuple[float, ...]], bool],
    code: str,
    subject: str,
    expected: str,
    remediation: str,
) -> list[ValidationIssue]:
    observations = experiment.observations
    vectors = _radius_vectors(observations)
    if not vectors:
        return []
    if observations.mode is RadiusAxisMode.SHARED:
        if not predicate(vectors[0]):
            return []
        return [
            ValidationIssue(
                code=code,
                message=f"the shared radius axis {subject}",
                severity=_WARNING,
                tiers=(_STRUCTURAL,),
                observed=f"{len(vectors[0])} radial position(s)",
                expected=expected,
                remediation=remediation,
                component="observations.radius",
            )
        ]
    if observations.n_scans != len(experiment.scans):
        return []
    affected = [
        scan.scan_id
        for scan, values in zip(experiment.scans, vectors, strict=True)
        if predicate(values)
    ]
    if not affected:
        return []
    return [
        _aggregate(
            code=code,
            message=f"the radius axis of {len(affected)} scan(s) {subject}",
            severity=_WARNING,
            tiers=(_STRUCTURAL,),
            subjects=affected,
            observed=f"{len(affected)} of {len(vectors)} scan(s)",
            expected=expected,
            remediation=remediation,
            component="observations.radius",
        )
    ]


def check_elapsed_time_monotonicity(
    experiment: AUCExperiment,
) -> list[ValidationIssue]:
    """Scans recorded out of time order are legitimate but worth reporting."""
    present = [
        (scan.scan_id, scan.elapsed_time.value)
        for scan in experiment.scans
        if _is_present(scan.elapsed_time) and scan.elapsed_time.value is not None
    ]
    values = [value for _, value in present]
    if len(values) < 2 or all(b >= a for a, b in pairwise(values)):
        return []
    offenders = [
        present[index + 1][0]
        for index, (current, following) in enumerate(pairwise(values))
        if following < current
    ]
    return [
        _aggregate(
            code="elapsed_time_not_monotonic",
            message="elapsed time does not increase with scan order",
            severity=_WARNING,
            tiers=(_STRUCTURAL,),
            subjects=offenders,
            observed=f"{len(offenders)} scan(s) earlier than their predecessor",
            expected="non-decreasing elapsed time across scans in order",
            remediation="verify scan ordering; openauc never reorders scans",
            component="scan.elapsed_time",
        )
    ]


def check_mixed_optical_systems(experiment: AUCExperiment) -> list[ValidationIssue]:
    """More than one declared optical system in one observation set.

    Only *declared* systems are counted: a mixture of ``UNKNOWN`` and a declared
    system is partial metadata, not a genuine mix.
    """
    declared = {
        scan.optical_system
        for scan in experiment.scans
        if scan.optical_system is not OpticalSystem.UNKNOWN
    }
    if len(declared) < 2:
        return []
    names = sorted(system.value for system in declared)
    return [
        ValidationIssue(
            code="mixed_optical_systems",
            message=f"scans declare more than one optical system: {names}",
            severity=_WARNING,
            tiers=(_STRUCTURAL,),
            observed=", ".join(names),
            expected=(
                "one optical system per observation set, because the set "
                "carries a single signal unit"
            ),
            remediation="split the scans into one experiment per optical system",
            component="scan.optical_system",
        )
    ]


def check_mixed_declared_units(experiment: AUCExperiment) -> list[ValidationIssue]:
    """One per-scan field declaring more than one unit across scans."""
    issues: list[ValidationIssue] = []
    for field in _SCAN_QUANTITY_FIELDS:
        accessor = _SCAN_QUANTITY_ACCESSORS[field]
        units: set[Unit] = set()
        for scan in experiment.scans:
            quantity = accessor(scan)
            if quantity is not None and _is_present(quantity):
                units.add(quantity.unit)
        if len(units) < 2:
            continue
        names = sorted(unit.value for unit in units)
        issues.append(
            ValidationIssue(
                code="mixed_declared_units",
                message=f"{field} declares more than one unit across scans: {names}",
                severity=_WARNING,
                tiers=(_STRUCTURAL,),
                observed=", ".join(names),
                expected=f"one declared unit for {field} across all scans",
                remediation=(
                    "declare the unit consistently at source; openauc never "
                    "converts units"
                ),
                component=f"scan.{field}",
            )
        )
    return issues


def check_cell_and_channel(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Cell and channel are organisational; their absence is informational."""
    issues: list[ValidationIssue] = []
    for field in ("cell", "channel"):
        instrument_value = (
            getattr(experiment.instrument, field)
            if experiment.instrument is not None
            else None
        )
        if instrument_value is not None:
            continue
        absent = [
            scan.scan_id for scan in experiment.scans if getattr(scan, field) is None
        ]
        if not absent:
            continue
        issues.append(
            _aggregate(
                code=f"{field}_absent",
                message=f"{len(absent)} scan(s) record no {field}",
                severity=_INFO,
                tiers=(_STRUCTURAL,),
                subjects=absent,
                observed=f"{len(absent)} of {len(experiment.scans)} scan(s)",
                expected=f"a {field} on each scan, or on the instrument",
                remediation=f"record the {field} in the manifest if it is known",
                component=f"scan.{field}",
            )
        )
    return issues


# --------------------------------------------------------------------------- #
# READINESS tiers — metadata a future workflow would need
# --------------------------------------------------------------------------- #


def check_elapsed_time_absent(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Sedimentation velocity is inherently a time series; equilibrium is not."""
    absent = [
        scan.scan_id for scan in experiment.scans if not _is_present(scan.elapsed_time)
    ]
    if not absent:
        return []
    return [
        _aggregate(
            code="elapsed_time_absent",
            message=f"{len(absent)} scan(s) carry no elapsed time",
            severity=_WARNING,
            tiers=(_SV,),
            blocks=(_SV,),
            subjects=absent,
            observed=f"{len(absent)} of {len(experiment.scans)} scan(s)",
            expected="an elapsed time on every scan for a velocity workflow",
            remediation="supply elapsed_seconds in the data file or manifest",
            component="scan.elapsed_time",
        )
    ]


def check_insufficient_scans_for_sv(
    experiment: AUCExperiment,
) -> list[ValidationIssue]:
    """A velocity workflow needs at least two scans carrying observations."""
    if not experiment.scans:
        return []
    observations = experiment.observations
    if observations.n_scans != len(experiment.scans):
        return []
    populated = sum(1 for count in observations.points_per_scan() if count > 0)
    if populated >= 2:
        return []
    return [
        ValidationIssue(
            code="insufficient_scans_for_sv",
            message=(
                f"only {populated} scan(s) carry observations; a velocity "
                "workflow needs a time series"
            ),
            severity=_WARNING,
            tiers=(_SV,),
            blocks=(_SV,),
            observed=f"{populated} populated scan(s)",
            expected="at least two scans carrying observations",
            remediation="include the remaining scans of the run",
            component="observations",
        )
    ]


def check_rotor_speed_absent(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Rotor speed is unavoidable in both workflows.

    Satisfied by a per-scan speed on every scan, or by the instrument's nominal
    speed.
    """
    if _is_present(_instrument_quantity(experiment, "nominal_speed")):
        return []
    absent = [
        scan.scan_id for scan in experiment.scans if not _is_present(scan.rotor_speed)
    ]
    if not absent:
        return []
    return [
        _aggregate(
            code="rotor_speed_absent",
            message=f"{len(absent)} scan(s) carry no rotor speed",
            severity=_WARNING,
            tiers=_READINESS,
            blocks=_READINESS,
            subjects=absent,
            observed=f"{len(absent)} of {len(experiment.scans)} scan(s), and no "
            "instrument nominal speed",
            expected="a per-scan rotor speed, or an instrument nominal speed",
            remediation="record rotor_speed_rpm per scan or nominal_speed_rpm",
            component="scan.rotor_speed",
        )
    ]


def check_experiment_type_unknown(experiment: AUCExperiment) -> list[ValidationIssue]:
    """An undeclared type does not make data unanalysable; it is not blocking."""
    if experiment.metadata.experiment_type is not ExperimentType.UNKNOWN:
        return []
    return [
        ValidationIssue(
            code="experiment_type_unknown",
            message="the experiment type is not declared",
            severity=_WARNING,
            tiers=_READINESS,
            observed=ExperimentType.UNKNOWN.value,
            expected="a declared experiment type",
            remediation="set experiment_type in the manifest if it is known",
            component="metadata.experiment_type",
        )
    ]


def check_temperature_absent(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Temperature enables standard-condition correction, not analysis itself."""
    if _is_present(_instrument_quantity(experiment, "temperature")):
        return []
    absent = [
        scan.scan_id for scan in experiment.scans if not _is_present(scan.temperature)
    ]
    if not absent:
        return []
    return [
        _aggregate(
            code="temperature_absent",
            message=f"{len(absent)} scan(s) carry no temperature",
            severity=_WARNING,
            tiers=_READINESS,
            subjects=absent,
            observed=f"{len(absent)} of {len(experiment.scans)} scan(s), and no "
            "instrument temperature",
            expected="a per-scan or instrument temperature",
            remediation="record temperature_c if it is known",
            component="scan.temperature",
        )
    ]


def check_absorbance_wavelength_absent(
    experiment: AUCExperiment,
) -> list[ValidationIssue]:
    """Wavelength is needed to interpret absorbance quantitatively."""
    if _is_present(_instrument_quantity(experiment, "wavelength")):
        return []
    absent = [
        scan.scan_id
        for scan in experiment.scans
        if scan.optical_system is OpticalSystem.ABSORBANCE
        and not _is_present(scan.wavelength)
    ]
    if not absent:
        return []
    return [
        _aggregate(
            code="absorbance_wavelength_absent",
            message=f"{len(absent)} absorbance scan(s) carry no wavelength",
            severity=_WARNING,
            tiers=_READINESS,
            subjects=absent,
            observed=f"{len(absent)} absorbance scan(s) without a wavelength",
            expected="a wavelength on absorbance scans, or on the instrument",
            remediation="record wavelength_nm if it is known",
            component="scan.wavelength",
        )
    ]


def check_signal_unit_unknown(experiment: AUCExperiment) -> list[ValidationIssue]:
    """An unknown signal unit blocks quantitative interpretation, not analysis."""
    if experiment.observations.signal_unit is not Unit.UNKNOWN:
        return []
    return [
        ValidationIssue(
            code="signal_unit_unknown",
            message="the signal unit is not declared",
            severity=_WARNING,
            tiers=_READINESS,
            observed=Unit.UNKNOWN.value,
            expected="a declared signal unit",
            remediation="declare signal_unit in the manifest defaults",
            component="observations.signal_unit",
        )
    ]


def check_optical_system_unknown(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Scans with no declared optical system, and no instrument fallback."""
    if (
        experiment.instrument is not None
        and experiment.instrument.optical_system is not OpticalSystem.UNKNOWN
    ):
        return []
    absent = [
        scan.scan_id
        for scan in experiment.scans
        if scan.optical_system is OpticalSystem.UNKNOWN
    ]
    if not absent:
        return []
    return [
        _aggregate(
            code="optical_system_unknown",
            message=f"{len(absent)} scan(s) declare no optical system",
            severity=_WARNING,
            tiers=_READINESS,
            subjects=absent,
            observed=f"{len(absent)} of {len(experiment.scans)} scan(s)",
            expected="a declared optical system per scan, or on the instrument",
            remediation="declare optical_system in the manifest defaults",
            component="scan.optical_system",
        )
    ]


def check_no_samples(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Sample metadata is not needed to obtain a sedimentation coefficient."""
    if experiment.samples:
        return []
    return [
        ValidationIssue(
            code="no_samples",
            message="the experiment records no sample metadata",
            severity=_WARNING,
            tiers=_READINESS,
            observed="0 samples",
            expected="at least one sample record",
            remediation="add a samples block to the manifest if it is known",
            component="samples",
        )
    ]


def check_sample_fields(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Report absent physico-chemical sample metadata without requiring it.

    None of these block a readiness tier: they enable standard-condition
    correction and molar-mass interpretation, which are downstream of the
    workflows themselves.
    """
    if not experiment.samples:
        return []
    issues: list[ValidationIssue] = []
    specs: tuple[
        tuple[str, ValidationSeverity, tuple[ValidationTier, ...], str], ...
    ] = (
        ("buffer_description", _INFO, (_SE,), "the buffer composition"),
        ("density", _WARNING, _READINESS, "solvent density"),
        ("viscosity", _WARNING, _READINESS, "solvent viscosity"),
        ("partial_specific_volume", _WARNING, (_SE,), "partial specific volume"),
    )
    for field, severity, tiers, label in specs:
        absent = [
            sample.sample_id
            for sample in experiment.samples
            if _sample_field_absent(sample, field)
        ]
        if not absent:
            continue
        issues.append(
            _aggregate(
                code=f"{field}_absent",
                message=f"{len(absent)} sample(s) record no {label}",
                severity=severity,
                tiers=tiers,
                subjects=absent,
                observed=f"{len(absent)} of {len(experiment.samples)} sample(s)",
                expected=f"{label} recorded on each sample",
                remediation=f"record {field} in the manifest samples block",
                component=f"sample.{field}",
                are_scans=False,
            )
        )
    return issues


def _sample_field_absent(sample: SampleMetadata, field: str) -> bool:
    if field == "buffer_description":
        description = sample.buffer_description
        return description is None or not description.strip()
    return not _is_present(_SAMPLE_QUANTITY_ACCESSORS[field](sample))


def check_provenance_absent(experiment: AUCExperiment) -> list[ValidationIssue]:
    """A hand-built experiment legitimately carries no provenance."""
    if experiment.provenance is not None:
        return []
    return [
        ValidationIssue(
            code="provenance_absent",
            message="no import provenance is recorded",
            severity=_INFO,
            tiers=(_ARCHIVAL,),
            observed="provenance is None",
            expected="an ImportProvenance record for imported experiments",
            remediation="load the experiment through openauc.load to record it",
            component="provenance",
        )
    ]


def check_source_checksum_absent(experiment: AUCExperiment) -> list[ValidationIssue]:
    """Checksum computation is intentionally deferred to the AUCX phase.

    Reported as informational only. It never affects structural validity or any
    readiness tier, and it never appears in ``validate_structure()``.
    """
    provenance = experiment.provenance
    if provenance is None or provenance.sha256 is not None:
        return []
    return [
        ValidationIssue(
            code="source_checksum_absent",
            message=(
                "no source checksum is recorded; checksum computation is "
                "intentionally deferred to the AUCX phase (ADR-0003)"
            ),
            severity=_INFO,
            tiers=(_ARCHIVAL,),
            observed="sha256 is None",
            expected="no checksum is expected before the AUCX phase",
            remediation="none required; this is an accepted deferral",
            component="provenance.sha256",
        )
    ]


#: The fixed execution order. Report order follows this list exactly.
CHECKS: tuple[Check, ...] = (
    check_duplicate_scan_ids,
    check_duplicate_sample_ids,
    check_no_scans,
    check_scan_observation_correspondence,
    check_non_physical_radius,
    check_optical_signal_unit_conflict,
    check_empty_scans,
    check_no_observations,
    check_radius_monotonicity,
    check_duplicate_radius,
    check_elapsed_time_monotonicity,
    check_mixed_optical_systems,
    check_mixed_declared_units,
    check_cell_and_channel,
    check_elapsed_time_absent,
    check_insufficient_scans_for_sv,
    check_rotor_speed_absent,
    check_experiment_type_unknown,
    check_temperature_absent,
    check_absorbance_wavelength_absent,
    check_signal_unit_unknown,
    check_optical_system_unknown,
    check_no_samples,
    check_sample_fields,
    check_provenance_absent,
    check_source_checksum_absent,
)
