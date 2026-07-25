"""Tiered validation: blocking sets, severities, determinism (scenarios 1-5,
7, 9, 12, 15, 16, 17, 20)."""

from __future__ import annotations

import json

import pytest

from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    ExperimentType,
    ImportProvenance,
    InstrumentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    SampleMetadata,
    ScanMetadata,
    Unit,
    ValidationIssue,
    ValidationSeverity,
    ValidationTier,
    ValueProvenance,
    ValueStatus,
)


def _scan(
    scan_id: str,
    index: int,
    *,
    optical: OpticalSystem = OpticalSystem.ABSORBANCE,
    elapsed: float | None = None,
) -> ScanMetadata:
    value = float(index) * 60.0 if elapsed is None else elapsed
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=Quantity.of(value, Unit.SECOND),
        optical_system=optical,
    )


def _shared(
    scan_ids: list[str], signal_unit: Unit = Unit.ABSORBANCE_UNIT
) -> Observations:
    return Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.1, 0.2, 0.3] for _ in scan_ids],
        scan_ids=scan_ids,
        signal_unit=signal_unit,
    )


def _experiment(**overrides: object) -> AUCExperiment:
    defaults: dict[str, object] = {
        "metadata": ExperimentMetadata(experiment_id="e"),
        "scans": (_scan("a", 0), _scan("b", 1)),
        "observations": _shared(["a", "b"]),
    }
    defaults.update(overrides)
    return AUCExperiment(**defaults)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 1 & 2 — the permissive minimum, and a fully described experiment
# --------------------------------------------------------------------------- #


def test_minimal_archival_experiment_has_no_blocking_findings() -> None:
    """A bare experiment is archivable and structurally valid (scenario 1)."""
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="historic-1"),
        scans=(ScanMetadata(scan_id="s1", index=0, elapsed_time=Quantity.missing()),),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1], signal=[[0.1, 0.2]], scan_ids=["s1"]
        ),
    )
    report = experiment.validate()
    assert report.is_valid
    assert report.errors == ()
    assert report.blocking_for(ValidationTier.ARCHIVAL) == ()
    assert report.blocking_for(ValidationTier.STRUCTURAL) == ()
    # Sparse metadata is reported, never required.
    assert "elapsed_time_absent" in report.codes()


def test_structurally_complete_experiment_reports_nothing_blocking() -> None:
    """A fully described experiment produces no blocking findings (scenario 2)."""
    scans = tuple(
        ScanMetadata(
            scan_id=f"s{index}",
            index=index,
            elapsed_time=Quantity.of(float(index) * 600.0, Unit.SECOND),
            cell="1",
            channel="A",
            wavelength=Quantity.of(280.0, Unit.NANOMETRE),
            optical_system=OpticalSystem.ABSORBANCE,
            rotor_speed=Quantity.of(45000.0, Unit.RPM),
            temperature=Quantity.of(20.0, Unit.DEGREE_CELSIUS),
        )
        for index in range(3)
    )
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(
            experiment_id="complete-1",
            experiment_type=ExperimentType.SEDIMENTATION_VELOCITY,
        ),
        scans=scans,
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3]] * 3,
            scan_ids=[scan.scan_id for scan in scans],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
        samples=(
            SampleMetadata(
                sample_id="sample-1",
                buffer_description="synthetic buffer",
                density=Quantity.of(1.0, Unit.OTHER, unit_label="g/mL"),
                viscosity=Quantity.of(0.01, Unit.OTHER, unit_label="P"),
                partial_specific_volume=Quantity.of(
                    0.73, Unit.OTHER, unit_label="mL/g"
                ),
            ),
        ),
        instrument=InstrumentMetadata(optical_system=OpticalSystem.ABSORBANCE),
        provenance=ImportProvenance(parser_name="hand-built", sha256="a" * 64),
    )
    report = experiment.validate()
    assert report.is_valid
    assert report.warnings == ()
    assert report.infos == ()


# --------------------------------------------------------------------------- #
# 3-5 — the blocking sets
# --------------------------------------------------------------------------- #


def test_no_scans_blocks_structural_but_not_archival() -> None:
    """Scenario 3: an empty scan set is archivable but not inspectable."""
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(),
        observations=Observations.from_per_scan(
            radii=[], signals=[], scan_ids=[], signal_unit=Unit.ABSORBANCE_UNIT
        ),
    )
    report = experiment.validate()
    issue = report.by_code("no_scans")[0]
    assert issue.severity is ValidationSeverity.ERROR
    assert issue.tier is ValidationTier.STRUCTURAL
    assert not issue.blocks_tier(ValidationTier.ARCHIVAL)
    assert issue.blocks_tier(ValidationTier.STRUCTURAL)
    assert issue.blocks_structural_validity
    assert report.blocking_for(ValidationTier.ARCHIVAL) == ()


def test_duplicate_scan_identifiers_block_archival() -> None:
    """Scenario 4."""
    experiment = _experiment(scans=(_scan("dup", 0), _scan("dup", 1)))
    report = experiment.validate()
    issue = report.by_code("duplicate_scan_id")[0]
    assert issue.severity is ValidationSeverity.ERROR
    assert issue.tier is ValidationTier.ARCHIVAL
    assert issue.blocks_tier(ValidationTier.ARCHIVAL)
    assert issue.location == "dup"
    assert issue.remediation is not None


def test_duplicate_sample_identifiers_block_archival() -> None:
    experiment = _experiment(
        samples=(
            SampleMetadata(sample_id="s"),
            SampleMetadata(sample_id="s"),
        )
    )
    codes = experiment.validate().codes()
    assert "duplicate_sample_id" in codes


def test_scan_count_mismatch_blocks_archival() -> None:
    """Scenario 5."""
    experiment = _experiment(scans=(_scan("a", 0),))
    issue = experiment.validate().by_code("scan_count_mismatch")[0]
    assert issue.blocks_tier(ValidationTier.ARCHIVAL)
    assert issue.observed is not None


def test_per_scan_checks_stand_down_when_correspondence_is_broken() -> None:
    """A count mismatch is reported once; per-scan checks do not compound it."""
    experiment = _experiment(
        scans=(_scan("a", 0),),
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.2, 6.1], []],
            signals=[[0.1, 0.2, 0.3], []],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    report = experiment.validate()
    assert report.by_code("scan_count_mismatch")
    assert report.by_code("empty_scan") == ()
    assert report.by_code("radius_not_monotonic") == ()


def test_scan_id_mismatch_blocks_archival() -> None:
    experiment = _experiment(observations=_shared(["a", "c"]))
    issue = experiment.validate().by_code("scan_id_mismatch")[0]
    assert issue.blocks_tier(ValidationTier.ARCHIVAL)


def test_non_physical_radius_blocks_structural() -> None:
    experiment = _experiment(
        scans=(_scan("a", 0),),
        observations=Observations.from_shared_axis(
            radius=[0.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3]],
            scan_ids=["a"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    issue = experiment.validate().by_code("non_physical_radius")[0]
    assert issue.blocks_tier(ValidationTier.STRUCTURAL)


# --------------------------------------------------------------------------- #
# 7, 9, 12, 15 — structural anomalies that never block
# --------------------------------------------------------------------------- #


def test_non_monotonic_elapsed_time_is_a_non_blocking_warning() -> None:
    """Scenario 7: out-of-order scans are legitimate."""
    experiment = _experiment(
        scans=(_scan("a", 0, elapsed=600.0), _scan("b", 1, elapsed=0.0))
    )
    report = experiment.validate()
    issue = report.by_code("elapsed_time_not_monotonic")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()
    assert report.is_valid
    assert issue.scan_ids == ("b",)


def test_unknown_optical_system_is_reported_but_never_a_conflict() -> None:
    """Scenario 9."""
    experiment = _experiment(
        scans=(_scan("a", 0, optical=OpticalSystem.UNKNOWN),),
        observations=_shared(["a"], Unit.FRINGE),
    )
    report = experiment.validate()
    assert report.is_valid
    assert report.by_code("optical_signal_unit_conflict") == ()
    issue = report.by_code("optical_system_unknown")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()


def test_empty_per_scan_and_fully_empty_experiment() -> None:
    """Scenario 12, both axis modes."""
    per_scan = _experiment(
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.1], []],
            signals=[[0.1, 0.2], []],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        )
    )
    report = per_scan.validate()
    assert report.is_valid
    empty = report.by_code("empty_scan")[0]
    assert empty.severity is ValidationSeverity.WARNING
    assert empty.location == "b"
    assert report.by_code("no_observations") == ()

    fully_empty = _experiment(
        scans=(_scan("a", 0),),
        observations=Observations.from_shared_axis(
            radius=[], signal=[[]], scan_ids=["a"], signal_unit=Unit.ABSORBANCE_UNIT
        ),
    )
    none_left = fully_empty.validate().by_code("no_observations")[0]
    assert none_left.severity is ValidationSeverity.WARNING
    assert none_left.blocks_tier(ValidationTier.SV_READINESS)
    assert none_left.blocks_tier(ValidationTier.SE_READINESS)
    assert not none_left.blocks_structural_validity


def test_mixed_optical_systems_is_a_structural_warning() -> None:
    """Scenario 15: only declared systems count as a mix."""
    experiment = _experiment(
        scans=(
            _scan("a", 0, optical=OpticalSystem.ABSORBANCE),
            _scan("b", 1, optical=OpticalSystem.UNKNOWN),
        )
    )
    assert experiment.validate().by_code("mixed_optical_systems") == ()

    mixed = _experiment(
        scans=(
            _scan("a", 0, optical=OpticalSystem.ABSORBANCE),
            _scan("b", 1, optical=OpticalSystem.FLUORESCENCE),
        ),
        observations=_shared(["a", "b"], Unit.UNKNOWN),
    )
    issue = mixed.validate().by_code("mixed_optical_systems")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.blocks == ()


def test_radius_anomalies_are_warnings_in_both_modes() -> None:
    descending = _experiment(
        scans=(_scan("a", 0),),
        observations=Observations.from_shared_axis(
            radius=[6.2, 6.1, 6.0],
            signal=[[0.1, 0.2, 0.3]],
            scan_ids=["a"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    # Descending order is legitimate and must not be flagged.
    assert descending.validate().by_code("radius_not_monotonic") == ()

    wobbly = _experiment(
        scans=(_scan("a", 0),),
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.2, 6.1],
            signal=[[0.1, 0.2, 0.3]],
            scan_ids=["a"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    issue = wobbly.validate().by_code("radius_not_monotonic")[0]
    assert issue.severity is ValidationSeverity.WARNING
    assert issue.scan_ids == ()

    per_scan_duplicate = _experiment(
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.0, 6.1], [6.0, 6.1, 6.2]],
            signals=[[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        )
    )
    duplicate = per_scan_duplicate.validate().by_code("duplicate_radius_within_scan")[0]
    assert duplicate.scan_ids == ("a",)
    assert duplicate.severity is ValidationSeverity.WARNING


def test_shared_axis_duplicate_radius_is_reported_once() -> None:
    experiment = _experiment(
        observations=Observations.from_shared_axis(
            radius=[6.0, 6.0, 6.1],
            signal=[[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        )
    )
    issues = experiment.validate().by_code("duplicate_radius_within_scan")
    assert len(issues) == 1
    assert issues[0].scan_ids == ()


def test_mixed_declared_units_are_reported_per_field() -> None:
    experiment = _experiment(
        scans=(
            _scan("a", 0),
            ScanMetadata(
                scan_id="b",
                index=1,
                elapsed_time=Quantity(
                    value=60.0,
                    unit=Unit.UNKNOWN,
                    status=ValueStatus.PRESENT,
                    provenance=ValueProvenance.SUPPLIED,
                ),
                optical_system=OpticalSystem.ABSORBANCE,
            ),
        )
    )
    issue = experiment.validate().by_code("mixed_declared_units")[0]
    assert issue.component == "scan.elapsed_time"
    assert issue.severity is ValidationSeverity.WARNING


def test_cell_and_channel_absence_is_informational() -> None:
    experiment = _experiment()
    report = experiment.validate()
    for code in ("cell_absent", "channel_absent"):
        issue = report.by_code(code)[0]
        assert issue.severity is ValidationSeverity.INFO
        assert issue.blocks == ()
        assert issue.scan_ids == ("a", "b")
    # An instrument-level value satisfies the check.
    with_instrument = _experiment(instrument=InstrumentMetadata(cell="1", channel="A"))
    assert with_instrument.validate().by_code("cell_absent") == ()


# --------------------------------------------------------------------------- #
# 16 & 17 — provenance and checksum policy
# --------------------------------------------------------------------------- #


def test_absent_provenance_is_informational() -> None:
    """Scenario 16."""
    issue = _experiment().validate().by_code("provenance_absent")[0]
    assert issue.severity is ValidationSeverity.INFO
    assert issue.tier is ValidationTier.ARCHIVAL
    assert issue.blocks == ()


def test_absent_checksum_is_informational_and_excluded_from_validate_structure() -> (
    None
):
    """Scenario 17: the policy is INFO only, and never structural."""
    experiment = _experiment(provenance=ImportProvenance(parser_name="generic-long"))
    issue = experiment.validate().by_code("source_checksum_absent")[0]
    assert issue.severity is ValidationSeverity.INFO
    assert issue.blocks == ()
    assert "deferred" in issue.message
    assert experiment.validate_structure().by_code("source_checksum_absent") == ()
    # Recording a checksum removes the finding entirely.
    with_checksum = _experiment(
        provenance=ImportProvenance(parser_name="x", sha256="b" * 64)
    )
    assert with_checksum.validate().by_code("source_checksum_absent") == ()


# --------------------------------------------------------------------------- #
# 20 — determinism
# --------------------------------------------------------------------------- #


def test_validation_is_deterministic_across_equivalent_experiments() -> None:
    """Scenario 20: equivalent inputs produce equivalent reports."""
    first = _experiment(scans=(_scan("b", 0), _scan("a", 1)))
    second = _experiment(scans=(_scan("b", 0), _scan("a", 1)))
    assert first.validate().issues == second.validate().issues
    assert first.validate().codes() == first.validate().codes()
    assert first.validate().to_dict() == second.validate().to_dict()


def test_aggregated_scan_ids_are_sorted() -> None:
    experiment = _experiment(
        scans=(_scan("z", 0), _scan("m", 1), _scan("a", 2)),
        observations=_shared(["z", "m", "a"]),
    )
    issue = experiment.validate().by_code("rotor_speed_absent")[0]
    assert issue.scan_ids == ("a", "m", "z")
    assert issue.location is None


# --------------------------------------------------------------------------- #
# Report and issue plumbing
# --------------------------------------------------------------------------- #


def test_validate_structure_is_a_subset_of_validate() -> None:
    experiment = _experiment()
    full = experiment.validate()
    structural = experiment.validate_structure()
    assert set(structural.issues).issubset(set(full.issues))
    assert all(
        issue.severity is not ValidationSeverity.INFO for issue in structural.issues
    )
    assert all(
        ValidationTier.ARCHIVAL in issue.tiers
        or ValidationTier.STRUCTURAL in issue.tiers
        for issue in structural.issues
    )


def test_report_counts_and_filters() -> None:
    report = _experiment().validate()
    errors, warnings, infos = report.counts()
    assert (errors, warnings, infos) == (
        len(report.errors),
        len(report.warnings),
        len(report.infos),
    )
    readiness_only = report.for_tiers(ValidationTier.SV_READINESS)
    assert all(
        ValidationTier.SV_READINESS in issue.tiers for issue in readiness_only.issues
    )
    assert (
        report.for_tiers(
            ValidationTier.STRUCTURAL, severities=(ValidationSeverity.ERROR,)
        ).issues
        == ()
    )


def test_report_serialises_to_json() -> None:
    payload = _experiment().validate().to_dict()
    assert json.loads(json.dumps(payload))["is_valid"] is True
    assert payload["counts"]["error"] == 0


def test_issue_describe_includes_detail() -> None:
    issue = _experiment().validate().by_code("rotor_speed_absent")[0]
    described = issue.describe()
    assert "tiers:" in described
    assert "expected:" in described
    assert "remediation:" in described


def test_issue_requires_at_least_one_tier() -> None:
    with pytest.raises(ValueError, match="at least one tier"):
        ValidationIssue(code="x", message="y", tiers=())


def test_readiness_findings_never_use_error_severity() -> None:
    """The severity policy is what keeps the tiers from collapsing together."""
    readiness_tiers = {ValidationTier.SV_READINESS, ValidationTier.SE_READINESS}
    experiment = _experiment(scans=(_scan("a", 0),))
    for issue in experiment.validate().issues:
        if set(issue.tiers).issubset(readiness_tiers):
            assert issue.severity is not ValidationSeverity.ERROR
