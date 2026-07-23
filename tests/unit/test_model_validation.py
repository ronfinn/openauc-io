"""Structural validation: duplicates, mismatch, optical/unit, report (7, 10, 16)."""

from __future__ import annotations

import pytest

from openauc.exceptions import StructuralValidationError
from openauc.models import (
    AUCExperiment,
    ExperimentMetadata,
    Observations,
    OpticalSystem,
    Quantity,
    ScanMetadata,
    Unit,
    ValidationSeverity,
)


def _scan(scan_id: str, index: int, optical: OpticalSystem) -> ScanMetadata:
    return ScanMetadata(
        scan_id=scan_id,
        index=index,
        elapsed_time=Quantity.of(float(index) * 60.0, Unit.SECOND),
        optical_system=optical,
    )


def _shared(scan_ids: list[str], signal_unit: Unit) -> Observations:
    return Observations.from_shared_axis(
        radius=[6.0, 6.1, 6.2],
        signal=[[0.1, 0.2, 0.3] for _ in scan_ids],
        scan_ids=scan_ids,
        signal_unit=signal_unit,
    )


def test_duplicate_scan_identifiers_reported() -> None:
    # Observations enforce unique scan_ids, so the duplication lives in the scan
    # metadata; structural validation must still surface it.
    scans = (
        _scan("dup", 0, OpticalSystem.ABSORBANCE),
        _scan("dup", 1, OpticalSystem.ABSORBANCE),
    )
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=scans,
        observations=_shared(["dup", "other"], Unit.ABSORBANCE_UNIT),
    )
    report = experiment.validate_structure()
    assert not report.is_valid
    codes = {issue.code for issue in report.errors}
    assert "duplicate_scan_id" in codes


def test_scan_count_mismatch_reported() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.ABSORBANCE),),
        observations=_shared(["a", "b"], Unit.ABSORBANCE_UNIT),
    )
    report = experiment.validate_structure()
    assert not report.is_valid
    assert "scan_count_mismatch" in {i.code for i in report.errors}


def test_scan_id_mismatch_reported() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(
            _scan("a", 0, OpticalSystem.ABSORBANCE),
            _scan("b", 1, OpticalSystem.ABSORBANCE),
        ),
        observations=_shared(["a", "c"], Unit.ABSORBANCE_UNIT),
    )
    report = experiment.validate_structure()
    assert "scan_id_mismatch" in {i.code for i in report.errors}


def test_optical_signal_unit_conflict_reported() -> None:
    # Absorbance optical system with a fringe signal unit is a defined conflict.
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.ABSORBANCE),),
        observations=_shared(["a"], Unit.FRINGE),
    )
    report = experiment.validate_structure()
    assert "optical_signal_unit_conflict" in {i.code for i in report.errors}


def test_unknown_optical_system_does_not_conflict() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.UNKNOWN),),
        observations=_shared(["a"], Unit.FRINGE),
    )
    assert experiment.validate_structure().is_valid


def test_non_physical_radius_reported() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.ABSORBANCE),),
        observations=Observations.from_shared_axis(
            radius=[0.0, 6.1, 6.2],
            signal=[[0.1, 0.2, 0.3]],
            scan_ids=["a"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    report = experiment.validate_structure()
    assert "non_physical_radius" in {i.code for i in report.errors}


def test_empty_per_scan_is_warning_not_error() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(
            _scan("a", 0, OpticalSystem.ABSORBANCE),
            _scan("b", 1, OpticalSystem.ABSORBANCE),
        ),
        observations=Observations.from_per_scan(
            radii=[[6.0, 6.1], []],
            signals=[[0.1, 0.2], []],
            scan_ids=["a", "b"],
            signal_unit=Unit.ABSORBANCE_UNIT,
        ),
    )
    report = experiment.validate_structure()
    assert report.is_valid  # a warning does not invalidate
    assert any(
        i.severity is ValidationSeverity.WARNING and i.code == "empty_scan"
        for i in report.issues
    )


def test_report_str_and_raise_if_invalid() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.ABSORBANCE),),
        observations=_shared(["a"], Unit.FRINGE),
    )
    report = experiment.validate_structure()
    assert "FAILED" in str(report)
    with pytest.raises(StructuralValidationError):
        report.raise_if_invalid()


def test_valid_report_str_and_raise_noop() -> None:
    experiment = AUCExperiment(
        metadata=ExperimentMetadata(experiment_id="e"),
        scans=(_scan("a", 0, OpticalSystem.ABSORBANCE),),
        observations=_shared(["a"], Unit.ABSORBANCE_UNIT),
    )
    report = experiment.validate_structure()
    assert report.is_valid
    assert "OK" in str(report)
    report.raise_if_invalid()  # must not raise
