"""Analysis readiness: routing, blocking sets, and the permanent
non-assessment (scenarios 6, 8, 10, 11, 23, 24)."""

from __future__ import annotations

import json

import pytest

from openauc.models import (
    AnalysisKind,
    AUCExperiment,
    ExperimentMetadata,
    ExperimentType,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    ReadinessStatus,
    SampleMetadata,
    ScanMetadata,
    Unit,
    ValidationSeverity,
    ValidationTier,
)


def _scan(
    scan_id: str,
    index: int,
    *,
    elapsed: float | None = 0.0,
    optical: OpticalSystem = OpticalSystem.ABSORBANCE,
    wavelength: float | None = 280.0,
    rotor: float | None = 45000.0,
    temperature: float | None = 20.0,
) -> ScanMetadata:
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=(
            Quantity.of(elapsed, Unit.SECOND)
            if elapsed is not None
            else Quantity.missing()
        ),
        optical_system=optical,
        wavelength=(
            Quantity.of(wavelength, Unit.NANOMETRE) if wavelength is not None else None
        ),
        rotor_speed=Quantity.of(rotor, Unit.RPM) if rotor is not None else None,
        temperature=(
            Quantity.of(temperature, Unit.DEGREE_CELSIUS)
            if temperature is not None
            else None
        ),
    )


def _experiment(
    scans: tuple[ScanMetadata, ...],
    *,
    experiment_type: ExperimentType = ExperimentType.SEDIMENTATION_VELOCITY,
    samples: tuple[SampleMetadata, ...] = (),
    instrument: InstrumentMetadata | None = None,
) -> AUCExperiment:
    return AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e", experiment_type=experiment_type),
        scans=scans,
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3] for _ in scans],
            scan_ids=[scan.scan_id for scan in scans],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
        samples=samples,
        instrument=instrument,
    )


def _velocity_ready() -> AUCExperiment:
    return _experiment((_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0)))


# --------------------------------------------------------------------------- #
# 8 — experiment-type routing
# --------------------------------------------------------------------------- #


def test_velocity_type_routes_se_to_not_applicable() -> None:
    assessment = _velocity_ready().assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.NOT_APPLICABLE
    assert "velocity" in (assessment.sedimentation_equilibrium.note or "")


def test_equilibrium_type_routes_sv_to_not_applicable() -> None:
    experiment = _experiment(
        (_scan("a", 0), _scan("b", 1)),
        experiment_type=ExperimentType.SEDIMENTATION_EQUILIBRIUM,
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.NOT_APPLICABLE
    assert (
        assessment.sedimentation_equilibrium.status is ReadinessStatus.POTENTIALLY_READY
    )


def test_unknown_type_assesses_both_with_a_non_blocking_warning() -> None:
    """Scenario 8: absence of a statement is not a statement of absence."""
    experiment = _experiment(
        (_scan("a", 0, elapsed=0.0), _scan("b", 1, elapsed=600.0)),
        experiment_type=ExperimentType.UNKNOWN,
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    assert (
        assessment.sedimentation_equilibrium.status is ReadinessStatus.POTENTIALLY_READY
    )
    issue = experiment.validate().by_code("experiment_type_unknown")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()


def test_other_type_routes_both_to_not_applicable() -> None:
    """OTHER is an explicit non-SV/non-SE statement, unlike UNKNOWN."""
    experiment = _experiment(
        (_scan("a", 0), _scan("b", 1)), experiment_type=ExperimentType.OTHER
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.NOT_APPLICABLE
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.NOT_APPLICABLE
    assert experiment.validate().by_code("experiment_type_unknown") == ()


# --------------------------------------------------------------------------- #
# 6 — elapsed time blocks velocity only
# --------------------------------------------------------------------------- #


def test_missing_elapsed_time_blocks_sv_but_not_se() -> None:
    """Scenario 6: equilibrium is time-independent."""
    experiment = _experiment(
        (_scan("a", 0, elapsed=None), _scan("b", 1, elapsed=None)),
        experiment_type=ExperimentType.UNKNOWN,
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.BLOCKED
    assert (
        assessment.sedimentation_equilibrium.status is ReadinessStatus.POTENTIALLY_READY
    )
    blocking = assessment.sedimentation_velocity.blocking_issues
    assert {issue.code for issue in blocking} == {"elapsed_time_absent"}
    assert assessment.sedimentation_velocity.is_blocked


def test_single_scan_blocks_sv_only() -> None:
    experiment = _experiment((_scan("a", 0),), experiment_type=ExperimentType.UNKNOWN)
    assessment = experiment.assess_readiness()
    codes = {i.code for i in assessment.sedimentation_velocity.blocking_issues}
    assert codes == {"insufficient_scans_for_sv"}
    assert (
        assessment.sedimentation_equilibrium.status is ReadinessStatus.POTENTIALLY_READY
    )


def test_missing_rotor_speed_blocks_both_and_instrument_satisfies_it() -> None:
    experiment = _experiment(
        (_scan("a", 0, rotor=None), _scan("b", 1, elapsed=600.0, rotor=None)),
        experiment_type=ExperimentType.UNKNOWN,
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.BLOCKED
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.BLOCKED

    with_instrument = _experiment(
        (_scan("a", 0, rotor=None), _scan("b", 1, elapsed=600.0, rotor=None)),
        experiment_type=ExperimentType.UNKNOWN,
        instrument=InstrumentMetadata(nominal_speed=Quantity.of(45000.0, Unit.RPM)),
    )
    assert with_instrument.validate().by_code("rotor_speed_absent") == ()


# --------------------------------------------------------------------------- #
# 10, 11 — advisory findings that never block
# --------------------------------------------------------------------------- #


def test_missing_absorbance_wavelength_is_advisory_only() -> None:
    """Scenario 10: wavelength is needed to interpret, not to analyse."""
    experiment = _experiment(
        (_scan("a", 0, wavelength=None), _scan("b", 1, elapsed=600.0, wavelength=None))
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    advisory = {i.code for i in assessment.sedimentation_velocity.advisory_issues}
    assert "absorbance_wavelength_absent" in advisory
    issue = experiment.validate().by_code("absorbance_wavelength_absent")[0]
    assert issue.blocks == ()
    # A non-absorbance scan is never asked for a wavelength.
    interference = _experiment(
        (
            _scan("a", 0, optical=OpticalSystem.INTERFERENCE, wavelength=None),
            _scan(
                "b",
                1,
                elapsed=600.0,
                optical=OpticalSystem.INTERFERENCE,
                wavelength=None,
            ),
        )
    )
    assert interference.validate().by_code("absorbance_wavelength_absent") == ()


def test_missing_sample_metadata_is_advisory_only() -> None:
    """Scenario 11."""
    experiment = _velocity_ready()
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    assert "no_samples" in {
        i.code for i in assessment.sedimentation_velocity.advisory_issues
    }
    issue = experiment.validate().by_code("no_samples")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()


def test_sparse_sample_fields_are_reported_without_blocking() -> None:
    experiment = _experiment(
        (_scan("a", 0), _scan("b", 1, elapsed=600.0)),
        samples=(SampleMetadata(sample_id="s1"),),
        experiment_type=ExperimentType.UNKNOWN,
    )
    report = experiment.validate()
    for code in (
        "density_absent",
        "viscosity_absent",
        "partial_specific_volume_absent",
        "buffer_description_absent",
    ):
        issue = report.by_code(code)[0]
        assert issue.blocks == ()
        assert issue.scan_ids == ()
        assert issue.location == "s1"
    assert report.by_code("buffer_description_absent")[0].severity is (
        ValidationSeverity.INFO
    )
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.POTENTIALLY_READY
    assert (
        assessment.sedimentation_equilibrium.status is ReadinessStatus.POTENTIALLY_READY
    )


def test_unknown_signal_unit_is_advisory_only() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(
            experiment_id="e", experiment_type=ExperimentType.SEDIMENTATION_VELOCITY
        ),
        scans=(_scan("a", 0), _scan("b", 1, elapsed=600.0)),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1],
            signal=[[0.1, 0.2], [0.1, 0.2]],
            scan_ids=["a", "b"],
        ),
    )
    issue = experiment.validate().by_code("signal_unit_unknown")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()
    assert (
        experiment.assess_readiness().sedimentation_velocity.status
        is ReadinessStatus.POTENTIALLY_READY
    )


# --------------------------------------------------------------------------- #
# 23, 24 — the separation, and the permanent non-assessment
# --------------------------------------------------------------------------- #


def test_structurally_valid_experiment_can_still_be_readiness_blocked() -> None:
    """Scenario 23: the two questions are answered independently."""
    experiment = _experiment(
        (_scan("a", 0, elapsed=None),), experiment_type=ExperimentType.UNKNOWN
    )
    assert experiment.validate_structure().is_valid
    assert experiment.validate().is_valid
    assert experiment.assess_readiness().sedimentation_velocity.is_blocked


def test_structural_error_also_blocks_both_readiness_tiers() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(),
        observations=Observations.from_per_scan(radii=[], signals=[], scan_ids=[]),
    )
    assert not experiment.validate_structure().is_valid
    assessment = experiment.assess_readiness()
    assert assessment.sedimentation_velocity.status is ReadinessStatus.BLOCKED
    assert assessment.sedimentation_equilibrium.status is ReadinessStatus.BLOCKED


def test_scientific_suitability_is_always_not_assessed() -> None:
    """Scenario 24: never derived, never concluded."""
    for experiment in (
        _velocity_ready(),
        _experiment((_scan("a", 0, elapsed=None),)),
    ):
        entry = experiment.assess_readiness().scientific_suitability
        assert entry.status is ReadinessStatus.NOT_ASSESSED
        assert entry.blocking_issues == ()
        assert entry.advisory_issues == ()
        assert "does not assess scientific validity" in (entry.note or "")


def test_assessment_lookup_and_serialisation() -> None:
    assessment = _velocity_ready().assess_readiness()
    assert len(assessment.entries) == 3
    assert (
        assessment.for_analysis(AnalysisKind.SEDIMENTATION_VELOCITY)
        is assessment.sedimentation_velocity
    )
    payload = assessment.to_dict()
    assert json.loads(json.dumps(payload))["entries"][0]["analysis"] == (
        "sedimentation_velocity"
    )
    assert "not_assessed" in str(assessment)


def test_assessment_lookup_rejects_unknown_analysis() -> None:
    assessment = _velocity_ready().assess_readiness()
    trimmed = type(assessment)(entries=assessment.entries[:1])
    with pytest.raises(KeyError):
        trimmed.for_analysis(AnalysisKind.SCIENTIFIC_SUITABILITY)


def test_blocking_issues_come_from_the_blocks_metadata() -> None:
    experiment = _experiment(
        (_scan("a", 0, elapsed=None),), experiment_type=ExperimentType.UNKNOWN
    )
    report = experiment.validate()
    blocking = report.blocking_for(ValidationTier.SV_READINESS)
    assert (
        blocking == experiment.assess_readiness().sedimentation_velocity.blocking_issues
    )
    assert all(issue.blocks_tier(ValidationTier.SV_READINESS) for issue in blocking)
